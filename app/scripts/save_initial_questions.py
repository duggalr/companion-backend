# Database
from sqlalchemy import select, desc
from sqlalchemy.orm import Session

import sys
sys.path.append('/Users/rahulduggal/Documents/new_projects/new_companion/companion_backend')
from app import models, utils
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