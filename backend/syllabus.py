"""
EXAMIX AI - canonical CBSE Class 9 Mathematics syllabus concept list.

Used two ways:
  1. Passed to the AI as the allowed set of concept names, so its
     output always matches strings the frontend can recognise exactly.
  2. Returned to the frontend as the full filter list on the concept
     selection screen, regardless of how many concepts the AI actually
     detected in the uploaded paper - so a single-topic paper doesn't
     leave the student stuck with only one option to pick from.
"""

CBSE_CLASS_9_MATHS_SYLLABUS = [
    "Number Systems",
    "Polynomials",
    "Coordinate Geometry",
    "Linear Equations in Two Variables",
    "Introduction to Euclid's Geometry",
    "Lines and Angles",
    "Triangles",
    "Quadrilaterals",
    "Areas of Parallelograms and Triangles",
    "Circles",
    "Constructions",
    "Heron's Formula",
    "Surface Areas and Volumes",
    "Statistics",
    "Probability",
]
