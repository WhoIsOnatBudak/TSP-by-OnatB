def orientation(a, b, c):
    return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])


def edges_intersect(a, b, c, d, coords, eps=1e-9):
    if len({a, b, c, d}) < 4:
        return False

    p1 = coords[a]
    p2 = coords[b]
    p3 = coords[c]
    p4 = coords[d]

    o1 = orientation(p1, p2, p3)
    o2 = orientation(p1, p2, p4)
    o3 = orientation(p3, p4, p1)
    o4 = orientation(p3, p4, p2)

    return (
        ((o1 > eps and o2 < -eps) or (o1 < -eps and o2 > eps))
        and ((o3 > eps and o4 < -eps) or (o3 < -eps and o4 > eps))
    )


def two_opt_cross_check(path, coords):
    optimized_path = path[:]
    n_cities = len(optimized_path)

    if n_cities < 4:
        return optimized_path

    changed = True
    while changed:
        changed = False

        for i in range(n_cities - 1):
            for j in range(i + 2, n_cities):
                if i == 0 and j == n_cities - 1:
                    continue

                a = optimized_path[i]
                b = optimized_path[(i + 1) % n_cities]
                c = optimized_path[j]
                d = optimized_path[(j + 1) % n_cities]

                if edges_intersect(a, b, c, d, coords):
                    optimized_path[i + 1:j + 1] = reversed(optimized_path[i + 1:j + 1])
                    changed = True

    return optimized_path
