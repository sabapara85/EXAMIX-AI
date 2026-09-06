"""
EXAMIX AI - Built-in EXPO DEMO MODE data.

This module contains:
1. A small sample CBSE Class 9 Mathematics question paper (as text),
   used to demonstrate the "upload -> OCR -> concepts" flow without
   needing a real file or API keys.
2. A small hand-written question bank, tagged by concept and question
   type, used to generate a "new" mixed practice paper locally when
   Google Vision / DeepSeek / OpenAI are not reachable (e.g. no
   internet at the expo). Each generation run shuffles + lightly
   varies numbers so papers don't look identical every time.

This keeps EXPO DEMO MODE fully self-contained and reliable.
"""

import random

DEMO_CONCEPTS = ["Polynomials", "Linear Equations in Two Variables", "Lines and Angles", "Statistics"]

SAMPLE_PAPER_TEXT = """CBSE Class 9 - Mathematics (Sample Practice Paper)

1. Find the zero of the polynomial p(x) = 2x + 5.

2. Factorise: x^2 + 7x + 10.

3. If x + y = 10 and 2x - y = 2, find the values of x and y.

4. Draw the graph of the linear equation 2x + y = 6.

5. In the given figure, two lines intersect at a point. If one angle is 40 degrees,
   find the measures of the remaining three angles.

6. If two adjacent angles are supplementary and one of them is 65 degrees, find the other.

7. Find the mean of the following data: 4, 8, 15, 16, 23, 42.

8. The marks obtained by 10 students in a test are:
   23, 45, 12, 34, 67, 45, 23, 12, 34, 45. Find the mode.

9. Represent 3x - 5 = 0 as a linear equation in two variables and find two solutions.

10. Verify whether x = 2 and y = 1 is a solution of the equation 3x - 2y = 4.
"""

# --- Question bank: concept -> list of question dicts -------------------
# Each question dict has: type ('mcq' | 'short' | 'long'), question,
# options (only for mcq, list of 4), answer, solution, concept.
# {a}, {b}, {c} placeholders are filled with small random integers at
# generation time so repeated demo runs don't look identical.

QUESTION_BANK = {
    "Polynomials": [
        {
            "type": "mcq",
            "question": "What is the degree of the polynomial p(x) = {a}x^3 - 2x^2 + x - 7?",
            "options": ["1", "2", "3", "4"],
            "answer": "3",
            "solution": "The degree of a polynomial is the highest power of x present in it. "
                        "Here the highest power of x is 3, so the degree is 3.",
        },
        {
            "type": "mcq",
            "question": "The zero of the polynomial p(x) = x - {a} is:",
            "options": ["{a}", "-{a}", "0", "1"],
            "answer": "{a}",
            "solution": "A zero of p(x) is the value of x for which p(x) = 0. "
                        "Setting x - {a} = 0 gives x = {a}.",
        },
        {
            "type": "short",
            "question": "Factorise the polynomial: x^2 + {a}x + {b}, where {a} = sum and {b} = product of two numbers whose factors you must find.",
            "answer": "Depends on chosen {a}, {b} (see solution).",
            "solution": "Find two numbers whose sum is {a} and product is {b}. "
                        "Split the middle term using these numbers and factor by grouping "
                        "to get the two linear factors.",
        },
        {
            "type": "long",
            "question": "Using the Remainder Theorem, find the remainder when x^3 - {a}x^2 + x - {b} is divided by (x - 1). Show all steps.",
            "answer": "Substitute x = 1 into the polynomial and simplify.",
            "solution": "By the Remainder Theorem, the remainder when p(x) is divided by (x - 1) "
                        "equals p(1). Substitute x = 1 into p(x) = x^3 - {a}x^2 + x - {b} and "
                        "simplify arithmetically to get the numeric remainder.",
        },
    ],
    "Linear Equations in Two Variables": [
        {
            "type": "mcq",
            "question": "Which of the following is a solution of the equation x + y = {a}?",
            "options": ["(1, {a_minus_1})", "(0, 0)", "({a}, {a})", "(-1, -1)"],
            "answer": "(1, {a_minus_1})",
            "solution": "Substitute each pair into x + y = {a}. Only (1, {a}-1) satisfies "
                        "1 + ({a}-1) = {a}, so it is the correct solution.",
        },
        {
            "type": "short",
            "question": "Solve for x and y: x + y = {a} and x - y = {b}.",
            "answer": "x = ({a}+{b})/2, y = ({a}-{b})/2",
            "solution": "Add the two equations to eliminate y: 2x = {a} + {b}, so "
                        "x = ({a}+{b})/2. Substitute back into x + y = {a} to find y.",
        },
        {
            "type": "long",
            "question": "Draw the graph of the linear equation {a}x + y = {b}. Find the coordinates where the line meets the x-axis and the y-axis.",
            "answer": "x-intercept and y-intercept computed from the equation.",
            "solution": "To find the x-intercept, put y = 0 and solve for x. To find the "
                        "y-intercept, put x = 0 and solve for y. Plot both points and join "
                        "them to draw the line.",
        },
    ],
    "Lines and Angles": [
        {
            "type": "mcq",
            "question": "Two angles are supplementary. If one angle is {a} degrees, the other is:",
            "options": ["{sup}", "{a}", "90", "{a}+90"],
            "answer": "{sup}",
            "solution": "Supplementary angles add up to 180 degrees. So the other angle is "
                        "180 - {a} = {sup} degrees.",
        },
        {
            "type": "short",
            "question": "Two lines intersect at a point forming four angles. One of the angles is {a} degrees. Find the other three angles.",
            "answer": "{a}, {sup}, {a}, {sup} (vertically opposite and adjacent angles).",
            "solution": "Vertically opposite angles are equal, and adjacent angles on a "
                        "straight line are supplementary. So the angles are {a}, 180-{a}, "
                        "{a}, and 180-{a} degrees in order around the point.",
        },
        {
            "type": "long",
            "question": "In a triangle, two angles measure {a} degrees and {b} degrees. Find the third angle and state which type of triangle it is (by angles).",
            "answer": "Third angle = 180 - {a} - {b} degrees.",
            "solution": "The angle sum property of a triangle states that all three angles "
                        "add up to 180 degrees. Subtract the two given angles from 180 to "
                        "find the third, then classify the triangle as acute, right, or "
                        "obtuse based on its largest angle.",
        },
    ],
    "Statistics": [
        {
            "type": "mcq",
            "question": "The mean of the numbers {a}, {b}, {c} is:",
            "options": ["{mean}", "{a}", "{b}", "{c}"],
            "answer": "{mean}",
            "solution": "Mean = (sum of observations) / (number of observations) = "
                        "({a}+{b}+{c})/3 = {mean}.",
        },
        {
            "type": "short",
            "question": "Find the mean of the data set: {a}, {b}, {c}, {a}, {b}.",
            "answer": "Sum divided by 5.",
            "solution": "Add all five values together and divide by the total number of "
                        "observations (5) to get the mean.",
        },
        {
            "type": "long",
            "question": "The marks scored by students in a class test are: {a}, {b}, {c}, {a}, {b}, {a}. Find the mean and the mode of this data, showing all working.",
            "answer": "Mean = sum/6; Mode = most frequent value ({a}).",
            "solution": "Mean is found by adding all values and dividing by the number of "
                        "values (6). Mode is the value that occurs most frequently in the "
                        "data set, which here is {a} since it repeats most often.",
        },
    ],
}


def _rand_fill(text: str, vals: dict) -> str:
    for k, v in vals.items():
        text = text.replace("{" + k + "}", str(v))
    return text


def generate_demo_paper(concepts, question_type: str, num_questions: int):
    """Build a mixed-concept paper purely from the local bank (no internet
    required). Returns a list of question dicts ready for the API response.
    """
    pool = []
    for concept in concepts:
        for q in QUESTION_BANK.get(concept, []):
            pool.append((concept, q))

    if not pool:
        return []

    if question_type != "Mixed":
        type_map = {"MCQ": "mcq", "Short Answer": "short", "Long Answer": "long"}
        wanted = type_map.get(question_type)
        filtered = [p for p in pool if p[1]["type"] == wanted]
        pool = filtered if filtered else pool

    random.shuffle(pool)

    questions = []
    i = 0
    while len(questions) < num_questions and pool:
        concept, template = pool[i % len(pool)]
        i += 1

        a = random.randint(3, 12)
        b = random.randint(2, 10)
        c = random.randint(4, 15)
        vals = {
            "a": a, "b": b, "c": c,
            "a_minus_1": a - 1,
            "sup": 180 - a,
            "mean": round((a + b + c) / 3, 2),
        }

        q_text = _rand_fill(template["question"], vals)
        answer = _rand_fill(template["answer"], vals)
        solution = _rand_fill(template["solution"], vals)
        options = None
        if template["type"] == "mcq" and "options" in template:
            options = [_rand_fill(o, vals) for o in template["options"]]

        questions.append({
            "type": template["type"],
            "question": q_text,
            "options": options,
            "answer": answer,
            "solution": solution,
            "concepts_used": [concept],
        })
        if len(questions) >= num_questions:
            break

    return questions[:num_questions]
