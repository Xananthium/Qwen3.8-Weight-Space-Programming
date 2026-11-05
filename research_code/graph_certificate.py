#!/usr/bin/env python3
"""Generic port of a triangulated-sphere proof checker; no HLE graph or key.

Supply faces as JSON arrays of vertex labels. Optional --new-edge checks the
empty-common-neighbor obstruction for adding a nonedge to a triangulation.
The input graph and this certificate are not a verifier of arbitrary prose.
"""
import argparse
from collections import defaultdict, deque
import json
from pathlib import Path


def verify(faces, new_edge=None):
    incidence = defaultdict(list)
    if any(len(face) != 3 or len(set(face)) != 3 for face in faces):
        raise ValueError('Expected nondegenerate triangular faces')
    vertices = {v for face in faces for v in face}
    for face_index, face in enumerate(faces):
        for i in range(3):
            a, b = face[i], face[(i+1) % 3]
            incidence[tuple(sorted((a, b)))].append((face_index, 1 if a < b else -1))
    n = len(vertices)
    assert n >= 4 and len(incidence) == 3*n-6 and len(faces) == 2*n-4
    assert all(len(uses) == 2 for uses in incidence.values())
    adjacency = defaultdict(list)
    for uses in incidence.values():
        (i, di), (j, dj) = uses
        adjacency[i].append((j, -di*dj))
        adjacency[j].append((i, -di*dj))
    orientation = {0: 1}
    queue = deque([0])
    while queue:
        i = queue.popleft()
        for j, relation in adjacency[i]:
            expected = orientation[i]*relation
            if j not in orientation:
                orientation[j] = expected
                queue.append(j)
            else:
                assert orientation[j] == expected
    assert len(orientation) == len(faces)
    neighbors = {v: set() for v in vertices}
    for a, b in incidence:
        neighbors[a].add(b)
        neighbors[b].add(a)
    for vertex in vertices:
        link = defaultdict(set)
        for face in faces:
            if vertex in face:
                a, b = [x for x in face if x != vertex]
                link[a].add(b)
                link[b].add(a)
        assert set(link) == neighbors[vertex] and all(len(ns) == 2 for ns in link.values())
        reached = {next(iter(link))}
        frontier = list(reached)
        while frontier:
            for other in link[frontier.pop()]:
                if other not in reached:
                    reached.add(other)
                    frontier.append(other)
        assert reached == set(link)
    result = {'vertices': n, 'edges': len(incidence), 'triangular_faces': len(faces),
              'connected_orientable_closed_vertex_manifold_chi2': True}
    if new_edge:
        a, b = new_edge
        assert a in vertices and b in vertices and a != b
        assert tuple(sorted((a, b))) not in incidence
        common = neighbors[a] & neighbors[b]
        result['new_edge_common_neighbors'] = len(common)
        result['at_least_two_crossings_certificate'] = not common
        result['theorem_scope'] = ('For a simple planar triangulation, adding a nonedge between vertices with no common neighbor cannot have zero or one crossing: deleting an original crossed edge from a one-crossing drawing would leave a maximal planar graph in which the new edge must lie in a triangle.')
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--faces', type=Path, required=True)
    parser.add_argument('--new-edge', nargs=2)
    args = parser.parse_args()
    print(json.dumps(verify(json.loads(args.faces.read_text()), args.new_edge), indent=2))


if __name__ == '__main__':
    main()
