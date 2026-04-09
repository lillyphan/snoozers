from collections import deque
def readFromFile(inFile):
    i = 0
    walls = 0
    inputM  = []
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
            elif i < rows+2:
                inputM[i-2] = list(line.strip())
            elif i == rows+2:
                numPortals = int(line.strip())
                for j in range(numPortals):
                    portals.append([])
            else:
                portals[i-3-rows] = line.strip().split()
            i += 1
    return walls, inputM, portals

def calcScore(inputM, portals):
    horseX, horseY = 0, 0
    #loop through the map to find horse position
    for i in range(len(inputM)):
        for j in range(len(inputM[i])):
            if inputM[i][j] == 'H':
                horseX, horseY = i, j

    #portal map to hookup one portal to another
    portalMap = {}
    for portal in portals:
        r1, c1, r2, c2 = int(portal[0]), int(portal[1]), int(portal[2]), int(portal[3])
         #add portals as key val pairs both ways
        portalMap[(r1, c1)] = (r2, c2)
        portalMap[(r2, c2)] = (r1, c1)

    #bfs from the horse
    visited = []
    queue = []
    queue.append((horseX, horseY))
    visited.append((horseX, horseY))
    total = 0
    head = 0  # points to the front of the queue

    while head < len(queue):
        x, y = queue[head]
        head += 1

        tile = inputM[x][y]

        #add point values
        if tile == '.': total += 1
        elif tile == 'H': total += 1
        elif tile == 'p': total += 1
        elif tile == 'a': total += 11
        elif tile == 'b': total += -4
        elif tile == 'c': total += 4

        #check for portal
        if tile == 'p':
            #get the x and y of the connecting portal
            px, py = portalMap[(x, y)]
            if (px, py) not in visited:
                visited.append((px, py))
                queue.append((px, py))

        #check neighbors
        directions = [(-1, 0), (1, 0), (0, -1), (0, 1)]
        for i in range(len(directions)):
            dx, dy = directions[i]
            #find new position
            nx, ny = x + dx, y + dy
            #check bounds
            if nx >= 0 and nx < len(inputM) and ny >= 0 and ny < len(inputM[nx]):
                if (nx, ny) not in visited and inputM[nx][ny] != '#' and inputM[nx][ny] != 'W':
                    visited.append((nx, ny))
                    queue.append((nx, ny))

    return total

if __name__ == "__main__":
    numWalls, teamIn, portals = readFromFile("our_new_input.txt")
    out_file = open("output.txt","w")
    number = str(calcScore(teamIn, portals))
    out_file.write(number)
    out_file.write("\n")
    
    with open("our_new_input.txt", 'r') as f:
        next(f,None)
        next(f,None)
        buffer = deque()
        first_line = True
        for line in f:
            buffer.append(line.rstrip('\n')) 
            if len(buffer) > 2:
                content = buffer.popleft()
                
                if not first_line:
                    out_file.write('\n')
                
                out_file.write(content)
                first_line = False