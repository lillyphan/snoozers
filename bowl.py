import math
import random
import copy
from collections import deque
from pathlib import Path


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
                for j in range(rows):
                    inputM.append([])
            elif i < rows + 2:
                inputM[i - 2] = list(line.strip())
            elif i == rows + 2:
                numPortals = int(line.strip())
                for j in range(numPortals):
                    portals.append([])
            else:
                portals[i - 3 - rows] = line.strip().split()
            i += 1
    return walls, inputM, portals


INVALID_PENALTY = -100000  #penality for bad things

def isPerimeter(x, y, grid):
    return x == 0 or x == len(grid) - 1 or y == 0 or y == len(grid[x]) - 1

def calcScore(inputM, portals, penalizeOpen=True):
    rows = len(inputM)
    horseX, horseY = 0, 0
    for i in range(rows):
        for j in range(len(inputM[i])):
            if inputM[i][j] == 'H':
                horseX, horseY = i, j

    portalMap = {}
    for portal in portals:
        r1, c1, r2, c2 = int(portal[0]), int(portal[1]), int(portal[2]), int(portal[3])
        portalMap[(r1, c1)] = (r2, c2)
        portalMap[(r2, c2)] = (r1, c1)

    visited = set()
    queue = [(horseX, horseY)]
    visited.add((horseX, horseY))
    total = 0
    reachedPerimeter = False
    head = 0

    while head < len(queue):
        x, y = queue[head]
        head += 1

        if isPerimeter(x, y, inputM):
            reachedPerimeter = True

        tile = inputM[x][y]
        if tile == '.':  total += 1
        elif tile == 'H': total += 1
        elif tile == 'p': total += 1
        elif tile == 'a': total += 11
        elif tile == 'b': total += -4
        elif tile == 'c': total += 4

        if tile == 'p' and (x, y) in portalMap:
            px, py = portalMap[(x, y)]
            if (px, py) not in visited:
                visited.add((px, py))
                queue.append((px, py))

        for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            nx, ny = x + dx, y + dy
            if 0 <= nx < rows and 0 <= ny < len(inputM[nx]):
                if (nx, ny) not in visited and inputM[nx][ny] != '#' and inputM[nx][ny] != 'W':
                    visited.add((nx, ny))
                    queue.append((nx, ny))

    if penalizeOpen and reachedPerimeter:
        return INVALID_PENALTY
    return total

WALL_FORBIDDEN = {'#', 'a', 'b', 'c', 'p', 'H', 'W'}

def wallCount(grid):
    """Count walls placed by the solver (not pre-placed 'W' tiles)."""
    return sum(1 for row in grid for cell in row if cell == 'W')

def placeable(grid, x, y):
    """True if we are allowed to put a new wall at (x, y)."""
    return grid[x][y] == '.'

def wallPositions(grid):
    """All (x,y) that currently hold a solver-placed wall."""
    return [(i, j) for i in range(len(grid))
            for j in range(len(grid[i])) if grid[i][j] == 'W']

def grassPositions(grid):
    """All (x,y) that are plain grass (placeable)."""
    return [(i, j) for i in range(len(grid))
            for j in range(len(grid[i])) if grid[i][j] == '.']


def simulatedAnnealing(grid, portals, wallBudget,
                       T_start=500.0, T_min=0.1, alpha=0.995,
                       iterations_per_temp=50):
    """
    Simulated annealing for Enclose Horse.

    Moves:
      - add wall   (if under budget and grass exists)
      - remove wall
      - move wall  (remove one, place at random grass tile)

    Invalid enclosures are NOT skipped; they receive INVALID_PENALTY so
    they can still be accepted at high temperature but are strongly
    discouraged (modification #1).
    """
    current = copy.deepcopy(grid)
    current_score = calcScore(current, portals)

    best = copy.deepcopy(current)
    best_score = current_score

    T = T_start

    while T > T_min:
        for _ in range(iterations_per_temp):
            candidate = copy.deepcopy(current)

            walls = wallPositions(candidate)
            grass = grassPositions(candidate)
            can_add = len(walls) < wallBudget and len(grass) > 0
            can_remove = len(walls) > 0
            can_move = can_remove and len(grass) > 0

            moves = []
            if can_add:    moves.append('add')
            if can_remove: moves.append('remove')
            if can_move:   moves.append('move')

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
                new_grass = grassPositions(candidate)
                if new_grass:
                    nx, ny = random.choice(new_grass)
                    candidate[nx][ny] = 'W'
                else:
                    pass

            candidate_score = calcScore(candidate, portals)

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
    mode: "anneal" to run optimization, 
          "score" to just calculate score of existing file
    """
    numWalls, grid, portals = readFromFile(file_in)
    
    if mode == "anneal":
        print(f"  Running Simulated Annealing on {file_in.name}...")
        final_grid, final_score = simulatedAnnealing(grid, portals, numWalls)
    else:
        print(f"  Calculating BFS Score for {file_in.name}...")
        # Just calculate score; no penalization if you want raw stats
        final_grid = grid
        final_score = calcScore(grid, portals, penalizeOpen=True)

    with open(file_out, "w") as out_file:
        out_file.write(str(final_score))
        for row in final_grid:
            out_file.write("\n" + "".join(row))

if __name__ == "__main__":
    local_folder_location = Path(__file__).resolve().parent
    all_inputs = local_folder_location / "inputs"
    
    output_folder = local_folder_location / "outputs"
    output_folder.mkdir(exist_ok=True)
    
    # CHANGE THIS TO "score" IF YOU JUST WANT BFS
    RUN_MODE = "score" 

    for file_path in all_inputs.glob("*.txt"):
        output_name = f"output_{file_path.name}"
        output_path = output_folder / output_name
        
        createOutput(file_path, output_path, mode=RUN_MODE)
