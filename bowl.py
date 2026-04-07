def minSol(inputM):
    horseX, horseY = 0, 0
    for i in range(len(inputM)):
        for j in range(len(inputM[i])):
            if inputM[i][j] == 'H':
                horseX = i
                horseY = j


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

if __name__ == "__main__":
    numWalls, teamIn, portals = readFromFile("our_new_input.txt")
    for row in teamIn:
        print(row)
    for portal in portals:
        print(portal)