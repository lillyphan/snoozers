import math
import random
import copy
from collections import deque
from pathlib import Path


INVALID_PENALTY = -100000  # penalty for invalid/open outputs

TILE_SCORE = {
    '.': 1,
    'H': 1,
    'p': 1,
    'a': 11,
    'b': -4,
    'c': 4,
}


def readFromFile(inFile):
    i = 0
    walls = 0
    inputM = []
    portals = []

    with open(inFile, 'r') as f:
        for line in f:
            if i == 0:
                walls = int(line.strip())

            elif i == 1:
                dims = line.strip().split()
                rows = int(dims[0])
                cols = int(dims[1])
                for _ in range(rows):
                    inputM.append([])

            elif i < rows + 2:
                inputM[i - 2] = list(line.strip())

            elif i == rows + 2:
                numPortals = int(line.strip())
                for _ in range(numPortals):
                    portals.append([])

            else:
                portals[i - 3 - rows] = line.strip().split()

            i += 1

    return walls, inputM, portals


def findHorse(grid):
    """Find the horse once and return its coordinates."""
    for i in range(len(grid)):
        for j in range(len(grid[i])):
            if grid[i][j] == 'H':
                return i, j
    raise ValueError("Horse 'H' not found in grid.")


def buildPortalMap(portals):
    """Build portal lookup once."""
    portalMap = {}
    for portal in portals:
        r1, c1, r2, c2 = map(int, portal)
        portalMap[(r1, c1)] = (r2, c2)
        portalMap[(r2, c2)] = (r1, c1)
    return portalMap


def isPerimeter(x, y, grid):
    return x == 0 or x == len(grid) - 1 or y == 0 or y == len(grid[x]) - 1


def isBlocked(cell):
    """Cells the horse cannot move through."""
    return cell == '#' or cell == 'W'


def floodReachable(grid, horseX, horseY, portalMap):
    """
    BFS from the horse.

    Returns:
        visited: 2D boolean array
        reachable_count: number of reachable cells
        perimeter_breaches: how many reachable cells lie on the perimeter
        enclosed: True if horse cannot reach perimeter, False otherwise
    """
    rows = len(grid)
    visited = [[False] * len(row) for row in grid]
    q = deque([(horseX, horseY)])
    visited[horseX][horseY] = True

    reachable_count = 0
    perimeter_breaches = 0

    while q:
        x, y = q.popleft()
        reachable_count += 1

        if isPerimeter(x, y, grid):
            perimeter_breaches += 1

        tile = grid[x][y]

        # Portal jump
        if tile == 'p' and (x, y) in portalMap:
            px, py = portalMap[(x, y)]
            if not visited[px][py]:
                visited[px][py] = True
                q.append((px, py))

        # 4-directional movement
        for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            nx, ny = x + dx, y + dy
            if 0 <= nx < rows and 0 <= ny < len(grid[nx]):
                if not visited[nx][ny] and not isBlocked(grid[nx][ny]):
                    visited[nx][ny] = True
                    q.append((nx, ny))

    enclosed = (perimeter_breaches == 0)
    return visited, reachable_count, perimeter_breaches, enclosed


def validate(grid, horseX, horseY, portalMap):
    """
    Output validity check:
    True only if the horse is enclosed.
    """
    _, _, _, enclosed = floodReachable(grid, horseX, horseY, portalMap)
    return enclosed


def calcScore(grid, horseX, horseY, portalMap, penalizeOpen=True):
    """
    Compute score of the current grid.
    If penalizeOpen is True and the horse can escape, return a large penalty.
    """
    visited, reachable_count, perimeter_breaches, enclosed = floodReachable(
        grid, horseX, horseY, portalMap
    )

    if penalizeOpen and not enclosed:
        # Penalty gets worse with more leaked area and wider openings
        return INVALID_PENALTY - (reachable_count * 10) - (perimeter_breaches * 50)

    total = 0
    for i in range(len(grid)):
        for j in range(len(grid[i])):
            if visited[i][j]:
                total += TILE_SCORE.get(grid[i][j], 0)

    return total


WALL_FORBIDDEN = {'#', 'a', 'b', 'c', 'p', 'H', 'W'}


def wallCount(grid):
    """Count walls placed by the solver (not pre-placed '#' tiles)."""
    return sum(1 for row in grid for cell in row if cell == 'W')


def placeable(grid, x, y):
    """True if we are allowed to put a new wall at (x, y)."""
    return grid[x][y] == '.'


def wallPositions(grid):
    """All (x,y) positions that currently hold a solver-placed wall."""
    return [
        (i, j)
        for i in range(len(grid))
        for j in range(len(grid[i]))
        if grid[i][j] == 'W'
    ]


def grassPositions(grid):
    """All (x,y) positions that are plain grass (placeable)."""
    return [
        (i, j)
        for i in range(len(grid))
        for j in range(len(grid[i]))
        if grid[i][j] == '.'
    ]


def strategicGrassPositions(grid, horseX, horseY, radius=12):
    """
    Returns grass tiles that are either:
    - near the horse, or
    - adjacent to an existing wall/obstacle
    """
    rows = len(grid)
    strategic_grass = []

    for i in range(rows):
        for j in range(len(grid[i])):
            if grid[i][j] != '.':
                continue

            # Rule 1: near the horse
            if abs(i - horseX) + abs(j - horseY) <= radius:
                strategic_grass.append((i, j))
                continue

            # Rule 2: adjacent to wall / placed wall
            is_adjacent = False
            for dx, dy in [
                (-1, 0), (1, 0), (0, -1), (0, 1),
                (-1, -1), (-1, 1), (1, -1), (1, 1)
            ]:
                ni, nj = i + dx, j + dy
                if 0 <= ni < rows and 0 <= nj < len(grid[ni]):
                    if grid[ni][nj] in ['#', 'W']:
                        is_adjacent = True
                        break

            if is_adjacent:
                strategic_grass.append((i, j))

    return strategic_grass


def simulatedAnnealing(
    grid,
    portalMap,
    horseX,
    horseY,
    wallBudget,
    T_start=500.0,
    T_min=0.1,
    alpha=0.995,
    iterations_per_temp=1000
):
    """
    Simulated annealing for Enclose Horse.

    Moves:
      - add wall
      - remove wall
      - move wall

    Invalid states are allowed during search, but strongly penalized.
    """
    current = copy.deepcopy(grid)
    current_score = calcScore(current, horseX, horseY, portalMap, penalizeOpen=True)

    best = copy.deepcopy(current)
    best_score = current_score

    T = T_start

    while T > T_min:
        for _ in range(iterations_per_temp):
            candidate = copy.deepcopy(current)

            walls = wallPositions(candidate)
            grass = strategicGrassPositions(candidate, horseX, horseY)

            can_add = len(walls) < wallBudget and len(grass) > 0
            can_remove = len(walls) > 0
            can_move = can_remove and len(grass) > 0

            moves = []
            if can_add:
                moves.append('add')
            if can_remove:
                moves.append('remove')
            if can_move:
                moves.append('move')

            if not moves:
                break

            move = random.choice(moves)

            if move == 'add':
                x, y = random.choice(grass)
                candidate[x][y] = 'W'

            elif move == 'remove':
                x, y = random.choice(walls)
                candidate[x][y] = '.'

            elif move == 'move':
                rx, ry = random.choice(walls)
                candidate[rx][ry] = '.'

                new_grass = strategicGrassPositions(candidate, horseX, horseY)
                if new_grass:
                    nx, ny = random.choice(new_grass)
                    candidate[nx][ny] = 'W'

            candidate_score = calcScore(candidate, horseX, horseY, portalMap, penalizeOpen=True)
            delta = candidate_score - current_score

            if delta > 0 or random.random() < math.exp(delta / T):
                current = candidate
                current_score = candidate_score

                if current_score > best_score:
                    best = copy.deepcopy(current)
                    best_score = current_score

        T *= alpha

    return best, best_score


def createOutput(file_in, file_out, mode="anneal"):
    """
    mode:
      - "anneal": run optimization
      - "score": calculate score of existing file
    """
    numWalls, grid, portals = readFromFile(file_in)

    horseX, horseY = findHorse(grid)
    portalMap = buildPortalMap(portals)

    if mode == "anneal":
        print(f"Running Simulated Annealing on {file_in.name}...")
        final_grid, final_score = simulatedAnnealing(
            grid=grid,
            portalMap=portalMap,
            horseX=horseX,
            horseY=horseY,
            wallBudget=numWalls
        )
    else:
        print(f"Calculating BFS Score for {file_in.name}...")
        final_grid = grid
        final_score = calcScore(final_grid, horseX, horseY, portalMap, penalizeOpen=True)

    is_valid = validate(final_grid, horseX, horseY, portalMap)

    with open(file_out, "w") as out_file:
        out_file.write(str(final_score))
        for row in final_grid:
            out_file.write("\n" + "".join(row))

    print(f"  Score: {final_score}")
    print(f"  Valid enclosure: {is_valid}")


if __name__ == "__main__":
    local_folder_location = Path(__file__).resolve().parent
    all_inputs = local_folder_location / "inputs"

    output_folder = local_folder_location / "carlos_output"
    output_folder.mkdir(exist_ok=True)

    # Change to "score" if you only want to score existing inputs
    RUN_MODE = "anneal"

    for file_path in all_inputs.glob("*1184.txt"):
        output_name = f"output_{file_path.name}"
        output_path = output_folder / output_name
        createOutput(file_path, output_path, mode=RUN_MODE)