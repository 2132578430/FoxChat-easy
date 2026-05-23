from typing import List
from collections import Counter


class Solution:
    def minWindow(self, s: str, t: str) -> str:
        map_t = Counter(t)
        map_s = Counter()
        ans_left = -1
        ans_right = -1
        left = 0

        for right, c in enumerate(s):
            map_s[c] += 1
            while map_s >= map_t:
                if right - left < ans_right - ans_left:
                    ans_left, ans_right = left, right
                map_s[s[left]] -= 1
                left += 1

        return "" if ans_left == -1 else s[ans_left: ans_right + 1]


if __name__ == '__main__':
    solution = Solution()
    s = "ADOBECODEBANC"
    t = "ABC"
    ans = solution.minWindow(s, t)

    print(ans)