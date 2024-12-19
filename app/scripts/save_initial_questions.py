# Database
import os
import sys
parent_dir_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))
sys.path.append(parent_dir_path)
from app import models
from app.database import SessionLocal

initial_question_list = [

    {
        'name': 'Find Palindromic Substrings',
        'question': 'Write a function that finds all palindromic substrings in a given string.',
        'input_output_list': [
            { 'input': '"abba"', 'output': '["a", "b", "bb", "abba"]', 'explanation': 'The string "abba" contains palindromes of various lengths, including "abba" itself.'},
            { 'input': '"racecar"', 'output': '["r", "a", "c", "e", "cec", "aceca", "racecar"]', 'explanation': 'The string "racecar" contains several palindromes, including the full string itself.'},
            { 'input': '"abc"', 'output': '["a", "b", "c"]', 'explanation': 'The string "abc" contains only single-character palindromes.'}
        ],
        'function_name': "find_palindromic_substrings",
        'starter_code': """def find_palindromic_substrings(s: str) -> list:
    raise NotImplementedError""",
        'solution': """
def find_palindromic_substrings(s: str) -> list:p
    def expand_around_center(left: int, right: int):
        while left >= 0 and right < len(s) and s[left] == s[right]:
            palindromes.append(s[left:right+1])
            left -= 1
            right += 1

    palindromes = []
    for i in range(len(s)):
        expand_around_center(i, i)       # Odd-length palindromes
        expand_around_center(i, i + 1)  # Even-length alindromes
    return palindromes
""",
        'time_complexity': 'O(n^2)',
        'test_case_list': [
            { 'input': '"abba"', 'expected_output': ["a", "b", "bb", "abba"]},
            { 'input': '"racecar"', 'expected_output': ["r", "a", "c", "e", "cec", "aceca", "racecar"] },
            { 'input': '"abc"', 'expected_output': ["a", "b", "c"] },
            { 'input': '"a"', 'expected_output': ["a"] },
            { 'input': '""', 'expected_output': [] },
            { 'input': '"madamimadam"', 'expected_output': ["m", "a", "d", "madam", "a", "m", "i", "madamimadam", "a", "d", "madam", "a", "m"] },
            { 'input': '"xyzzyx"', 'expected_output': ["x", "y", "z", "zz", "yzz", "xyzzyx"] },
            { 'input': '"noonracecar"', 'expected_output': ["n", "o", "noon", "o", "n", "r", "a", "c", "e", "cec", "aceca", "racecar"] },
            { 'input': '"abcbabcba"', 'expected_output': ["a", "b", "c", "bcb", "abcba", "bcbabcba", "b", "a"] },
            { 'input': '"xyzyxxyzz"', 'expected_output': ["x", "y", "z", "yzy", "xyzyx", "x", "y", "zz", "xyzz"] }
        ]
    },

    {
        'name': 'Longest Consecutive Sequence',
        'question': 'Write a function to find the length of the longest consecutive elements sequence in an unsorted array.',
        'input_output_list': [
            { 'input': '[100, 4, 200, 1, 3, 2]', 'output': '4', 'explanation': 'The longest consecutive sequence is [1, 2, 3, 4].' },
            { 'input': '[0, 3, 7, 2, 5, 8, 4, 6, 0, 1]', 'output': '9', 'explanation': 'The longest consecutive sequence is [0, 1, 2, 3, 4, 5, 6, 7, 8].' },
            { 'input': '[1, 2, 3, 4, 10]', 'output': '4', 'explanation': 'The longest consecutive sequence is [1, 2, 3, 4].' }
        ],
        'function_name': "longest_consecutive_sequence",
        'starter_code': """def longest_consecutive_sequence(nums: list) -> int:
    raise NotImplementedError""",
        'solution': """
def longest_consecutive_sequence(nums: list) -> int:
    if not nums:
        return 0
    num_set = set(nums)
    longest_streak = 0

    for num in num_set:
        if num - 1 not in num_set:
            current_num = num
            current_streak = 1

            while current_num + 1 in num_set:
                current_num += 1
                current_streak += 1

            longest_streak = max(longest_streak, current_streak)
    return longest_streak
""",
        'time_complexity': 'O(n)',
        'test_case_list': [
            { 'input': '[100, 4, 200, 1, 3, 2]', 'expected_output': 4 },
            { 'input': '[0, 3, 7, 2, 5, 8, 4, 6, 0, 1]', 'expected_output': 9 },
            { 'input': '[1, 2, 3, 4, 10]', 'expected_output': 4 },
            { 'input': '[]', 'expected_output': 0 },
            { 'input': '[1]', 'expected_output': 1 }
        ]
    },

    {
        'name': 'Maximum Subarray',
        'question': 'Write a function to find the maximum sum of a contiguous subarray in a given array.',
        'input_output_list': [
            { 'input': '[-2,1,-3,4,-1,2,1,-5,4]', 'output': '6', 'explanation': 'The maximum subarray is [4,-1,2,1], with a sum of 6.' },
            { 'input': '[1]', 'output': '1', 'explanation': 'The array contains only one element, which is the maximum sum.' },
            { 'input': '[5,4,-1,7,8]', 'output': '23', 'explanation': 'The maximum subarray is the entire array, with a sum of 23.' }
        ],
        'function_name': "max_subarray",
        'starter_code': """def max_subarray(nums: list) -> int:
    raise NotImplementedError""",
        'solution': """
def max_subarray(nums: list) -> int:
    max_current = max_global = nums[0]
    for i in range(1, len(nums)):
        max_current = max(nums[i], max_current + nums[i])
        max_global = max(max_global, max_current)
    return max_global
""",
        'time_complexity': 'O(n)',
        'test_case_list': [
            { 'input': '[-2,1,-3,4,-1,2,1,-5,4]', 'expected_output': 6 },
            { 'input': '[1]', 'expected_output': 1 },
            { 'input': '[5,4,-1,7,8]', 'expected_output': 23 },
            { 'input': '[-1,-2,-3,-4]', 'expected_output': -1 },
            { 'input': '[0,0,0,0]', 'expected_output': 0 }
        ]
    },

    {
        'name': 'Binary Tree Level Order Traversal',
        'question': 'Write a function to return the level order traversal of a binary tree (each level as a separate list).',
        'input_output_list': [
            { 'input': '[3,9,20,null,null,15,7]', 'output': '[[3], [9, 20], [15, 7]]', 'explanation': 'The binary tree has three levels.' },
            { 'input': '[1]', 'output': '[[1]]', 'explanation': 'The binary tree has only one level.' },
            { 'input': '[]', 'output': '[]', 'explanation': 'The tree is empty.' }
        ],
        'function_name': "level_order_traversal",
        'starter_code': """class TreeNode:
    def __init__(self, val=0, left=None, right=None):
        self.val = val
        self.left = left
        self.right = right

def level_order_traversal(root: TreeNode) -> list:
    raise NotImplementedError""",
        'solution': """
from collections import deque

def level_order_traversal(root: TreeNode) -> list:
    if not root:
        return []
    result, queue = [], deque([root])
    while queue:
        level = []
        for _ in range(len(queue)):
            node = queue.popleft()
            level.append(node.val)
            if node.left:
                queue.append(node.left)
            if node.right:
                queue.append(node.right)
        result.append(level)
    return result
""",
        'time_complexity': 'O(n)',
        'test_case_list': [
            { 'input': '[3,9,20,null,null,15,7]', 'expected_output': [[3], [9, 20], [15, 7]] },
            { 'input': '[1]', 'expected_output': [[1]] },
            { 'input': '[]', 'expected_output': [] },
            { 'input': '[1,2,3]', 'expected_output': [[1], [2, 3]] },
            { 'input': '[1,null,2,3]', 'expected_output': [[1], [2], [3]] }
        ]
    },

    {
        'name': 'String Compression',
        'question': 'Implement a function that compresses a string using the counts of repeated characters (e.g., "aaabb" -> "a3b2").',
        'input_output_list': [
            { 'input': '"aaabb"', 'output': '"a3b2"', 'explanation': 'The string "aaabb" has 3 consecutive "a"s followed by 2 consecutive "b"s.'},
            { 'input': '"abc"', 'output': '"a1b1c1"', 'explanation': 'The string "abc" contains no repeating characters, so each is followed by a count of 1.'},
            { 'input': '"aaAAaa"', 'output': '"a2A2a2"', 'explanation': 'The string "aaAAaa" alternates between lower and uppercase letters, compressing each group separately.'}
        ],
        'starter_code': """def compress_string(s: str) -> str:
    raise NotImplementedError""",
        'solution': """
def compress_string(s: str) -> str:
    if not s:
        return ""
    compressed = []
    count = 1
    for i in range(1, len(s)):
        if s[i] == s[i - 1]:
            count += 1
        else:
            compressed.append(s[i - 1] + str(count))
            count = 1
    compressed.append(s[-1] + str(count))
    return "".join(compressed)
""",
        'time_complexity': 'O(n)',
        'test_case_list': [
            { 'input': '"aaabb"', 'expected_output': "a3b2" },  # Basic repeated characters
            { 'input': '"abc"', 'expected_output': "a1b1c1" },  # No repeated characters
            { 'input': '"aaAAaa"', 'expected_output': "a2A2a2" },  # Case sensitivity
            { 'input': '""', 'expected_output': "" },  # Empty string
            { 'input': '"a"', 'expected_output': "a1" },  # Single character
            { 'input': '"aaaaaaa"', 'expected_output': "a7" },  # Single repeated character
            { 'input': '"aabbaa"', 'expected_output': "a2b2a2" },  # Alternating repeated characters
            { 'input': '"abccba"', 'expected_output': "a1b1c2b1a1" },  # Palindromic structure
            { 'input': '"112233"', 'expected_output': "112213" },  # Numerical characters
            { 'input': '"aabcccccaaa"', 'expected_output': "a2b1c5a3" }  # Mixed single and multiple repeated characters
        ],
    },

    {
        'name': 'Valid Parentheses',
        'question': 'Write a function to determine if a string containing parentheses is valid. A string is valid if all open parentheses are closed in the correct order.',
        'input_output_list': [
            { 'input': '"()"', 'output': 'True', 'explanation': 'The string contains a matching pair of parentheses.' },
            { 'input': '"()[]{}"', 'output': 'True', 'explanation': 'The string contains matching pairs of parentheses, brackets, and braces.' },
            { 'input': '"(]"', 'output': 'False', 'explanation': 'The string contains mismatched parentheses.' }
        ],
        'function_name': "is_valid_parentheses",
        'starter_code': """def is_valid_parentheses(s: str) -> bool:
    raise NotImplementedError""",
        'solution': """
def is_valid_parentheses(s: str) -> bool:
    stack = []
    mapping = {')': '(', ']': '[', '}': '{'}
    for char in s:
        if char in mapping:
            top_element = stack.pop() if stack else '#'
            if mapping[char] != top_element:
                return False
        else:
            stack.append(char)
    return not stack
""",
        'time_complexity': 'O(n)',
        'test_case_list': [
            { 'input': '"()"', 'expected_output': True },
            { 'input': '"()[]{}"', 'expected_output': True },
            { 'input': '"(]"', 'expected_output': False },
            { 'input': '"([{}])"', 'expected_output': True },
            { 'input': '"[{]}"', 'expected_output': False }
        ]
    },

    {
        'name': 'Find First and Last Position of Element in Sorted Array',
        'question': 'Write a function to find the starting and ending position of a given target in a sorted array. If the target is not found, return [-1, -1].',
        'input_output_list': [
            { 'input': '[5,7,7,8,8,10], 8', 'output': '[3, 4]', 'explanation': 'The target 8 appears in positions 3 and 4.' },
            { 'input': '[5,7,7,8,8,10], 6', 'output': '[-1, -1]', 'explanation': 'The target 6 does not appear in the array.' },
            { 'input': '[], 0', 'output': '[-1, -1]', 'explanation': 'The array is empty, so the target cannot be found.' }
        ],
        'function_name': "search_range",
        'starter_code': """def search_range(nums: list, target: int) -> list:
    raise NotImplementedError""",
        'solution': """
def search_range(nums: list, target: int) -> list:
    def find_bound(is_first):
        left, right = 0, len(nums) - 1
        while left <= right:
            mid = (left + right) // 2
            if nums[mid] > target or (is_first and nums[mid] == target):
                right = mid - 1
            else:
                left = mid + 1
        return left

    start = find_bound(True)
    end = find_bound(False) - 1
    if start <= end < len(nums) and nums[start] == target and nums[end] == target:
        return [start, end]
    return [-1, -1]
""",
        'time_complexity': 'O(log n)',
        'test_case_list': [
            { 'input': '[5,7,7,8,8,10], 8', 'expected_output': [3, 4] },
            { 'input': '[5,7,7,8,8,10], 6', 'expected_output': [-1, -1] },
            { 'input': '[], 0', 'expected_output': [-1, -1] },
            { 'input': '[2,2,2,2], 2', 'expected_output': [0, 3] },
            { 'input': '[1,3,5,7], 3', 'expected_output': [1, 1] }
        ]
    },

    {
        'name': 'Merge Intervals',
        'question': 'Write a function to merge all overlapping intervals in a list and return the merged intervals.',
        'input_output_list': [
            { 'input': '[[1,3],[2,6],[8,10],[15,18]]', 'output': '[[1,6],[8,10],[15,18]]', 'explanation': 'Intervals [1,3] and [2,6] overlap and are merged into [1,6].' },
            { 'input': '[[1,4],[4,5]]', 'output': '[[1,5]]', 'explanation': 'Intervals [1,4] and [4,5] overlap and are merged into [1,5].' },
            { 'input': '[[1,3],[4,5]]', 'output': '[[1,3],[4,5]]', 'explanation': 'No intervals overlap, so no merging is required.' }
        ],
        'function_name': "merge_intervals",
        'starter_code': """def merge_intervals(intervals: list) -> list:
    raise NotImplementedError""",
        'solution': """
def merge_intervals(intervals: list) -> list:
    if not intervals:
        return []
    intervals.sort(key=lambda x: x[0])
    merged = [intervals[0]]
    for current in intervals[1:]:
        last = merged[-1]
        if current[0] <= last[1]:
            last[1] = max(last[1], current[1])
        else:
            merged.append(current)
    return merged
""",
        'time_complexity': 'O(n log n)',
        'test_case_list': [
            { 'input': '[[1,3],[2,6],[8,10],[15,18]]', 'expected_output': [[1,6],[8,10],[15,18]] },
            { 'input': '[[1,4],[4,5]]', 'expected_output': [[1,5]] },
            { 'input': '[[1,3],[4,5]]', 'expected_output': [[1,3],[4,5]] },
            { 'input': '[[1,4]]', 'expected_output': [[1,4]] },
            { 'input': '[[6,8],[1,9],[2,4],[4,7]]', 'expected_output': [[1,9]] }
        ]
    }

]

db = SessionLocal()
for di in initial_question_list:
    pg_question_object = models.InitialPlaygroundQuestion(
        name = di['name'],
        text = di['question'],
        starter_code = di['starter_code'],
        solution_code = di['solution'],
        solution_time_complexity = di['time_complexity'],
        example_io_list = str(di['input_output_list']),
        test_case_list = str(di['test_case_list']),
    )
    db.add(pg_question_object)
    db.commit()
    db.refresh(pg_question_object)