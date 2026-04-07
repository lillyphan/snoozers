import sys

def minSol(inputM):
    horseX, horseY = 0, 0
    for i in range(len(inputM)):
        for j in range(len(inputM[i])):
            if inputM[i][j] == 'H':
                horseX = i
                horseY = j


def readInput():
    print("fix me")

if __name__ == "__main__":
    print("hello")