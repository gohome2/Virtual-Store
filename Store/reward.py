"""Initial reward v1.

One full-price sale is worth one point. The score rewards contribution profit
after discount and ingredient costs. The 5% opt-out limit is measured separately
on the fixed evaluation windows.
"""

from env import FULL_PRICE_CONTRIBUTION_KRW


def reward_v1(info):
    return info["profit_krw"] / FULL_PRICE_CONTRIBUTION_KRW
