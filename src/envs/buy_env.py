from __future__ import annotations

import gymnasium as gym
import numpy as np
from gymnasium import spaces


class BuyEnvHybridV5US(gym.Env):
    def __init__(
        self,
        data_dict: dict,
        feature_cols: list[str],
        threshold: float = 0.10,
        is_training: bool = True,
        balance_tickers: bool = False,
    ):
        super().__init__()
        self.feature_cols = feature_cols
        self.threshold = threshold
        self.is_training = is_training
        self.balance_tickers = balance_tickers
        self.samples = []
        self.pos_samples = []
        self.neg_samples = []
        self.ticker_samples = {}

        for ticker, df in data_dict.items():
            df = df.dropna(subset=["Next_Max_Return"])
            if len(df) == 0:
                continue
            states = df[feature_cols].values.astype(np.float32)
            future_rets = df["Next_Max_Return"].values.astype(np.float32)
            t_pos, t_neg = [], []
            for i in range(len(df)):
                sample = (states[i], float(future_rets[i]), ticker)
                self.samples.append(sample)
                if future_rets[i] >= threshold:
                    self.pos_samples.append(sample)
                    t_pos.append(sample)
                else:
                    self.neg_samples.append(sample)
                    t_neg.append(sample)
            self.ticker_samples[ticker] = {"pos": t_pos, "neg": t_neg}

        self.action_space = spaces.Discrete(2)
        self.observation_space = spaces.Box(-np.inf, np.inf, shape=(len(feature_cols),), dtype=np.float32)
        self.current_sample = None

    def reset(self, seed=None, options=None):
        if self.is_training:
            if self.balance_tickers and self.ticker_samples:
                ticker = np.random.choice(list(self.ticker_samples.keys()))
                t_data = self.ticker_samples[ticker]
                if np.random.rand() < 0.5 and t_data["pos"]:
                    self.current_sample = t_data["pos"][np.random.randint(len(t_data["pos"]))]
                elif t_data["neg"]:
                    self.current_sample = t_data["neg"][np.random.randint(len(t_data["neg"]))]
                else:
                    self.current_sample = self.samples[np.random.randint(len(self.samples))]
            else:
                if np.random.rand() < 0.5 and self.pos_samples:
                    self.current_sample = self.pos_samples[np.random.randint(len(self.pos_samples))]
                elif self.neg_samples:
                    self.current_sample = self.neg_samples[np.random.randint(len(self.neg_samples))]
                else:
                    self.current_sample = self.samples[np.random.randint(len(self.samples))]
        else:
            self.current_sample = self.samples[np.random.randint(len(self.samples))]
        return self.current_sample[0], {}

    def step(self, action):
        _, max_ret, _ = self.current_sample
        is_success = max_ret >= self.threshold
        if action == 1:
            reward = 1.0 if is_success else 0.0
        else:
            reward = 0.0 if is_success else 1.0
        return self.current_sample[0], reward, True, False, {}
