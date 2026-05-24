from typing import List
from collections import Counter


class Solution:
    def firstMissingPositive(self, nums: List[int]) -> int:
        n = len(nums)

        for i in range(0, n - 1):
            while nums[i] > 0 and nums[i] < n + 1 and nums[i] != i + 1:
                nums[i], nums[nums[i] - 1] = nums[nums[i] - 1], nums[i]

        for num in nums:
            if num - 1 != nums:
                return num
        return 0

if __name__ == '__main__':
    solution = Solution()
    num = []
    ans = solution.firstMissingPositive(s, t)

    print(ans)