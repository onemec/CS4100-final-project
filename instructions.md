# CS4100-final-project

Artificial Intelligence Final Project

## What our project does:

The main focus of our project is to enable students to explore their interests and better navigate the confusing
processes of prerequisites required for course registration. We're looking to cover scenarios such as:

- How many new courses you could take as a result of taking some particular course
- If you have any particular course(s) you wish to take, what the shortest path(s) are to them

## Our heuristic

In an abstract overview, our heuristic considers the following criteria:

- How many credits the course is
- How many incomplete `requirementSections` it contributes to (trying to maximize)
    - If there are two AND sections, prefer the one closer to completion
    - If they are comparable, or one may be preferred since the other's classes fulfill other category requirements...
- Should be able to identify "unavoidable" courses which it should consider you will definitely take eventually
    - and will only consider the question of when to take them

## TODO:

- Alternative/potential thing we could do:
    - Visualize the "bruteforce" (or search alg) option in NetworkX of taking all possible courses in first semester,
      second semester, etc. and having the graph of paths to courses
    - Switch to using a [Multipartite graph](https://networkx.org/documentation/stable/auto_examples/drawing/plot_multipartite_graph.html)