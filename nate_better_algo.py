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
    #reachedPerimeter = False
    perimeter_breaches = 0
    head = 0

    while head < len(queue):
        x, y = queue[head]
        head += 1

        if isPerimeter(x, y, inputM):
           # reachedPerimeter = True
           perimeter_breaches += 1

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

    if penalizeOpen and perimeter_breaches > 0 :
        # GRADIENT PENALTY: 
        # Base penalty (-100000) ensures it is always worse than a valid closed shape.
        # len(visited) penalizes the total area leaked. 
        # perimeter_breaches penalizes the width of the gap.
        # As walls close the gap, visited volume shrinks, and the score INCREASES.
        return -100000 - (len(visited) * 10) - (perimeter_breaches * 50)
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

def strategicGrassPositions(grid, horseX, horseY, radius=12):
    """Returns grass tiles adjacent to walls/obstacles or near the horse."""
    rows = len(grid)
    cols = len(grid[0])
    strategic_grass = []

    for i in range(rows):
        for j in range(cols):
            if grid[i][j] == '.':
                
                # Rule 1: Allow placement near the horse (Manhattan distance)
                if abs(i - horseX) + abs(j - horseY) <= radius:
                    strategic_grass.append((i, j))
                    continue
                
                # Rule 2: Allow placement adjacent to existing '#' or 'W'
                is_adjacent = False
                # Check all 8 directions (including diagonals to allow for corners)
                for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1), (-1, -1), (-1, 1), (1, -1), (1, 1)]:
                    ni, nj = i + dx, j + dy
                    if 0 <= ni < rows and 0 <= nj < cols:
                        if grid[ni][nj] in ['#', 'W']:
                            is_adjacent = True
                            break # No need to check other directions for this tile
                
                if is_adjacent:
                    strategic_grass.append((i, j))

    return strategic_grass

def simulatedAnnealing(grid, portals, wallBudget,
                       T_start=500.0, T_min=0.1, alpha=0.995,
                       iterations_per_temp=100):
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

    # Find Horse coordinates ONCE for the strategic grass function
    horseX, horseY = 0, 0
    for i in range(len(grid)):
        for j in range(len(grid[i])):
            if grid[i][j] == 'H':
                horseX, horseY = i, j

    T = T_start

    while T > T_min:
        for _ in range(iterations_per_temp):
            candidate = copy.deepcopy(current)

            walls = wallPositions(candidate)
            #grass = grassPositions(candidate)
            grass = strategicGrassPositions(candidate, horseX, horseY)
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
                new_grass = strategicGrassPositions(candidate, horseX, horseY)
                if new_grass:
                    nx, ny = random.choice(new_grass)
                    candidate[nx][ny] = 'W'

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

def check_enclosed(grid, portals):
    """
    Returns True if the horse is completely enclosed by walls/impassable tiles.
    Returns False if the horse can reach the perimeter.
    """
    rows = len(grid)
    horseX, horseY = 0, 0
    
    # Find the starting position of the horse ('H')
    for i in range(rows):
        for j in range(len(grid[i])):
            if grid[i][j] == 'H':
                horseX, horseY = i, j
                break

    # Build the portal map
    portalMap = {}
    for portal in portals:
        r1, c1, r2, c2 = int(portal[0]), int(portal[1]), int(portal[2]), int(portal[3])
        portalMap[(r1, c1)] = (r2, c2)
        portalMap[(r2, c2)] = (r1, c1)

    # Setup BFS tracking
    visited = set()
    queue = deque([(horseX, horseY)])
    visited.add((horseX, horseY))

    # Run the BFS
    while queue:
        x, y = queue.popleft()

        if isPerimeter(x, y, grid):
            return False

        tile = grid[x][y]

        if tile == 'p' and (x, y) in portalMap:
            px, py = portalMap[(x, y)]
            if (px, py) not in visited:
                visited.add((px, py))
                queue.append((px, py))

        for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            nx, ny = x + dx, y + dy
            if 0 <= nx < rows and 0 <= ny < len(grid[nx]):
                if (nx, ny) not in visited and grid[nx][ny] not in ('#', 'W'):
                    visited.add((nx, ny))
                    queue.append((nx, ny))

    return True
def validate_output(output_file_path, input_file_path, report_file=None):
    """
    Reads an output file to check if the claimed score matches the actual score,
    and uses BFS to verify if the horse is fully enclosed. Writes to an optional text file.
    """
    _, _, portals = readFromFile(input_file_path)
    
    with open(output_file_path, 'r') as f:
        lines = f.read().splitlines()
        
    if not lines:
        error_msg = f"Error: {output_file_path.name} is empty."
        print(error_msg)
        if report_file:
            report_file.write(error_msg + "\n")
        return False

    claimed_score = int(lines[0].strip())
    grid = [list(line) for line in lines[1:] if line.strip()]
    
    actual_score = calcScore(grid, portals, penalizeOpen=True)
    is_valid_enclosure = check_enclosed(grid, portals)
    score_matches = (claimed_score == actual_score)
    
    # Format the report text
    report = (
        f"--- Validating: {output_file_path.name} ---\n"
        f"Claimed Score : {claimed_score}\n"
        f"Actual Score  : {actual_score}\n"
        f"Score Match   : {'✅' if score_matches else '❌'}\n"
        f"Is Enclosed   : {'✅' if is_valid_enclosure else '❌'}\n"
        f"{'-' * 40}"
    )
    
    # Print to console AND write to the file
    print(report)
    if report_file:
        report_file.write(report + "\n")
    
    return score_matches and is_valid_enclosure
if __name__ == "__main__":
    local_folder_location = Path(__file__).resolve().parent
    all_inputs = local_folder_location / "inputs"
    
    output_folder = local_folder_location / "outputs"
    output_folder.mkdir(exist_ok=True)
    
    # Set this to "anneal", "score", or "validate"
    RUN_MODE = "anneal" 
    
    # Define where the report will be saved
    report_file_path = local_folder_location / "validation_report.txt"

    if RUN_MODE == "validate":
        print(f"Starting validation. Saving report to: {report_file_path.name}\n")
        
        # Open the report file once, then loop through everything
        with open(report_file_path, "w", encoding="utf-8") as report_file:
            for file_path in all_inputs.glob("*.txt"):
                output_name = f"output_{file_path.name}"
                output_path = output_folder / output_name
                
                if output_path.exists():
                    validate_output(output_path, file_path, report_file)
                else:
                    skip_msg = f"Skipping validation: {output_name} does not exist yet."
                    print(skip_msg)
                    report_file.write(skip_msg + "\n")
                    
        print(f"\n✅ Validation complete! Full report saved to {report_file_path.name}")
        
    else:
        # Run standard generation modes
        for file_path in all_inputs.glob("*1189.txt"):
            output_name = f"output_{file_path.name}"
            output_path = output_folder / output_name
            createOutput(file_path, output_path, mode=RUN_MODE)