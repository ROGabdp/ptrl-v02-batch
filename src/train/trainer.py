from __future__ import annotations

import multiprocessing
import shutil
from pathlib import Path
from typing import Any

from src.envs.buy_env import BuyEnvHybridV5US


def _copy_final(stage_dir: Path) -> Path:
    best = stage_dir / "best.zip"
    last = stage_dir / "last.zip"
    final = stage_dir / "final.zip"
    if best.exists():
        shutil.copy2(best, final)
    elif last.exists():
        shutil.copy2(last, final)
    else:
        raise RuntimeError(f"No best/last model to create final: {stage_dir}")
    return final


def _latest_checkpoint(stage_dir: Path) -> Path | None:
    cks = list(stage_dir.glob("checkpoint_step_*.zip"))
    if not cks:
        return None
    cks.sort(key=lambda p: int(p.stem.split("_")[-1]))
    return cks[-1]


def _find_resume_model(stage_dir: Path) -> Path | None:
    for p in [_latest_checkpoint(stage_dir), stage_dir / "last.zip", stage_dir / "best.zip"]:
        if p is not None and p.exists():
            return p
    return None


def _stage_status(stage_dir: Path, force: bool) -> tuple[str, Path | None]:
    final = stage_dir / "final.zip"
    if final.exists() and not force:
        return "skip_final_exists", final
    resume = _find_resume_model(stage_dir)
    if resume is not None:
        return "resume", resume
    return "fresh", None


def _make_callbacks(
    stage_dir: Path,
    eval_env,
    save_freq: int,
    eval_freq: int,
    n_eval_episodes: int,
):
    from stable_baselines3.common.callbacks import BaseCallback, CallbackList, EvalCallback

    class StepCheckpointCallback(BaseCallback):
        def __init__(self, save_freq: int, save_dir: Path):
            super().__init__()
            self.save_freq = save_freq
            self.save_dir = save_dir

        def _on_step(self) -> bool:
            if self.num_timesteps > 0 and self.num_timesteps % self.save_freq == 0:
                ck = self.save_dir / f"checkpoint_step_{self.num_timesteps}.zip"
                self.model.save(str(ck.with_suffix("")))
            return True

    tmp_best_dir = stage_dir / "_best_tmp"
    tmp_best_dir.mkdir(parents=True, exist_ok=True)
    cb = CallbackList(
        [
            StepCheckpointCallback(save_freq=save_freq, save_dir=stage_dir),
            EvalCallback(
                eval_env,
                best_model_save_path=str(tmp_best_dir),
                log_path=str(stage_dir / "eval_logs"),
                eval_freq=eval_freq,
                n_eval_episodes=n_eval_episodes,
                deterministic=True,
            ),
        ]
    )
    return cb, tmp_best_dir


def train_base(
    cfg: dict[str, Any],
    train_data: dict[str, Any],
    base_dir: Path,
    tb_dir: Path,
    dry_run: bool = False,
    force: bool = False,
) -> tuple[str, str]:
    status, marker = _stage_status(base_dir, force=force)
    if status == "skip_final_exists":
        return status, str(marker)
    if dry_run:
        return status, str(base_dir / "final.zip")

    from stable_baselines3 import PPO
    from stable_baselines3.common.env_util import make_vec_env
    from stable_baselines3.common.vec_env import DummyVecEnv, SubprocVecEnv

    base_dir.mkdir(parents=True, exist_ok=True)
    tcfg = cfg["train"]["pretrain"]
    feature_cols = cfg["features"]["feature_cols"]
    threshold = float(cfg["label"]["threshold"])

    n_envs = min(int(tcfg["n_envs_max"]), max(1, multiprocessing.cpu_count() - 1))
    buy_env = make_vec_env(
        BuyEnvHybridV5US,
        n_envs=n_envs,
        vec_env_cls=SubprocVecEnv,
        env_kwargs={
            "data_dict": train_data,
            "feature_cols": feature_cols,
            "threshold": threshold,
            "is_training": True,
            "balance_tickers": True,
        },
    )
    eval_env = make_vec_env(
        BuyEnvHybridV5US,
        n_envs=1,
        vec_env_cls=DummyVecEnv,
        env_kwargs={
            "data_dict": train_data,
            "feature_cols": feature_cols,
            "threshold": threshold,
            "is_training": False,
            "balance_tickers": False,
        },
    )

    ppo_params = {
        "learning_rate": float(tcfg["learning_rate"]),
        "n_steps": max(128, 2048 // n_envs),
        "batch_size": int(tcfg["batch_size"]),
        "ent_coef": float(tcfg["ent_coef"]),
        "device": "cpu",
        "policy_kwargs": dict(net_arch=[int(x) for x in tcfg["net_arch"]]),
        "verbose": 1,
        "tensorboard_log": str(tb_dir),
    }

    if status == "resume" and marker is not None:
        model = PPO.load(str(marker), env=buy_env, device="cpu")
    else:
        model = PPO("MlpPolicy", buy_env, **ppo_params)

    callbacks, tmp_best_dir = _make_callbacks(
        stage_dir=base_dir,
        eval_env=eval_env,
        save_freq=int(tcfg["save_freq"]),
        eval_freq=int(tcfg["eval_freq"]),
        n_eval_episodes=int(tcfg["n_eval_episodes"]),
    )
    model.learn(total_timesteps=int(tcfg["steps"]), callback=callbacks, tb_log_name="base_pretrain")
    model.save(str((base_dir / "last.zip").with_suffix("")))
    best_tmp = tmp_best_dir / "best_model.zip"
    if best_tmp.exists():
        shutil.copy2(best_tmp, base_dir / "best.zip")
    final = _copy_final(base_dir)
    buy_env.close()
    eval_env.close()
    return status, str(final)


def train_finetune_one(
    cfg: dict[str, Any],
    ticker: str,
    ticker_train_data: dict[str, Any],
    ticker_eval_data: dict[str, Any],
    base_final_path: str,
    finetune_stage_dir: Path,
    tb_dir: Path,
    dry_run: bool = False,
    force: bool = False,
) -> tuple[str, str]:
    status, marker = _stage_status(finetune_stage_dir, force=force)
    if status == "skip_final_exists":
        return status, str(marker)
    if dry_run:
        return status, str(finetune_stage_dir / "final.zip")

    from stable_baselines3 import PPO
    from stable_baselines3.common.env_util import make_vec_env
    from stable_baselines3.common.utils import get_schedule_fn
    from stable_baselines3.common.vec_env import DummyVecEnv, SubprocVecEnv

    finetune_stage_dir.mkdir(parents=True, exist_ok=True)
    tcfg = cfg["train"]["finetune"]
    feature_cols = cfg["features"]["feature_cols"]
    threshold = float(cfg["label"]["threshold"])
    n_envs = min(int(tcfg["n_envs_max"]), max(1, multiprocessing.cpu_count() - 1))

    buy_env = make_vec_env(
        BuyEnvHybridV5US,
        n_envs=n_envs,
        vec_env_cls=SubprocVecEnv,
        env_kwargs={
            "data_dict": ticker_train_data,
            "feature_cols": feature_cols,
            "threshold": threshold,
            "is_training": True,
            "balance_tickers": False,
        },
    )
    eval_env = make_vec_env(
        BuyEnvHybridV5US,
        n_envs=1,
        vec_env_cls=DummyVecEnv,
        env_kwargs={
            "data_dict": ticker_eval_data,
            "feature_cols": feature_cols,
            "threshold": threshold,
            "is_training": False,
            "balance_tickers": False,
        },
    )

    load_from = marker if status == "resume" and marker is not None else Path(base_final_path)
    model = PPO.load(str(load_from), env=buy_env, device="cpu")
    model.learning_rate = float(tcfg["learning_rate"])
    model.lr_schedule = get_schedule_fn(model.learning_rate)
    model.ent_coef = float(tcfg["ent_coef"])

    callbacks, tmp_best_dir = _make_callbacks(
        stage_dir=finetune_stage_dir,
        eval_env=eval_env,
        save_freq=int(tcfg["save_freq"]),
        eval_freq=int(tcfg["eval_freq"]),
        n_eval_episodes=int(tcfg["n_eval_episodes"]),
    )
    model.learn(total_timesteps=int(tcfg["steps"]), callback=callbacks, reset_num_timesteps=False, tb_log_name=f"ft_{ticker}")
    model.save(str((finetune_stage_dir / "last.zip").with_suffix("")))
    best_tmp = tmp_best_dir / "best_model.zip"
    if best_tmp.exists():
        shutil.copy2(best_tmp, finetune_stage_dir / "best.zip")
    final = _copy_final(finetune_stage_dir)
    buy_env.close()
    eval_env.close()
    return status, str(final)
