from pprint import pprint
from gurobipy import GRB, Model, quicksum
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
import sys
import urllib.request




# home page with main functions/page links
class Home(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Terraria NPC Optimizer")
        self.vbox = QVBoxLayout()
        self.setLayout(self.vbox)

        self.optimizeButton = QPushButton("Optimize")

        self.grid = QGridLayout()

        self.optimizeButton.clicked.connect(self.optimize)

        self.header = QLabel("Terraria NPC Optimizer")
        self.header.setFont(QFont('Arial', 25))
        self.header.setAlignment(Qt.AlignCenter)
        self.vbox.addWidget(self.header)
        self.vbox.addLayout(self.grid)

        self.grid.addWidget(QWrappedLabel("NPC Name:"), 0, 0)
        self.grid.addWidget(QWrappedLabel("NPC Picture:"), 1, 0)
        self.grid.addWidget(QWrappedLabel("Collected?"), 2, 0)
        self.grid.addWidget(QWrappedLabel("Prioritize?"), 3, 0)

        i = 1
        self.collectBox = []
        self.prioritizeBox = []
        for (id, name) in NPCDict.items():
            self.grid.addWidget(QWrappedLabel(name), 0, i)

            picLabel = QLabel('picture')
            picLabel.setMinimumSize(24, 46)
            picPixmap = QPixmap()
            picPixmap.loadFromData(NPCPics[id])
            picLabel.setPixmap(picPixmap)
            picLabel.setScaledContents(False)
            self.grid.addWidget(picLabel, 1, i)


            checkBox = QCheckBox()
            checkBox.setChecked(True)
            self.collectBox.append(checkBox)
            self.grid.addWidget(checkBox, 2, i)
            checkBox = QCheckBox()
            self.prioritizeBox.append(checkBox)
            self.grid.addWidget(checkBox, 3, i)

            i += 1

        self.grid.addWidget(QWrappedLabel("Check/Uncheck All"), 1, self.grid.columnCount())
        self.checkboxAllCollect = QCheckBox()
        self.checkboxAllCollect.clicked.connect(self.checkAllCollect)
        self.grid.addWidget(self.checkboxAllCollect, 2, self.grid.columnCount() - 1)
        self.checkboxAllPrioritize = QCheckBox()
        self.checkboxAllPrioritize.clicked.connect(self.checkAllPrioritize)
        self.grid.addWidget(self.checkboxAllPrioritize, 3, self.grid.columnCount() - 1)

        for i in range(self.grid.columnCount()):
            self.grid.setColumnMinimumWidth(i, 70)
        for i in range(self.grid.rowCount()):
            self.grid.setRowMinimumHeight(i, 50)

        self.pylonBox = QCheckBox("Fill biomes for pylons?")
        self.hbox = QHBoxLayout()
        self.hbox.addWidget(self.pylonBox)
        self.hbox.addWidget(self.optimizeButton)

        self.vbox.addLayout(self.hbox)
        self.setMinimumSize(1900, 400)

    def checkAllCollect(self):
        for box in self.collectBox:
            box.setChecked(self.checkboxAllCollect.isChecked())

    def checkAllPrioritize(self):
        for box in self.prioritizeBox:
            box.setChecked(self.checkboxAllPrioritize.isChecked())

    def optimize(self):

        self.optimizeButton.setText("Optimizing...")
        app.processEvents()

        # %% Create the model
        # %% ctrl return runs just this cell
        m = Model('TerrariaNPCOptimizer')

        collectList = [0 for i in range(26)]
        prioritizeList = [0 for i in range(26)]
        for (i, box) in enumerate(self.collectBox):
            if box.isChecked():
                collectList[i] = 1
        for (i, box) in enumerate(self.prioritizeBox):
            if box.isChecked():
                prioritizeList[i] = 1


        # %% add decision variables
        x = m.addVars(range(26), range(26), vtype = GRB.BINARY, name = 'x')
        y = m.addVars(range(26), range(8), vtype = GRB.BINARY, name = 'y')
        p = m.addVars(range(26), vtype = GRB.INTEGER, name = 'y', lb=0)

        # %% add constraints
        # m.addConstrs((quicksum([x[i, j] for j in range(26)]) >= 1 for i in range(26)), name = "NPC has one roommate")
        m.addConstrs((p[i] >= quicksum([x[i, j] for j in range(26)]) - 3 for i in range(26)), name = "set penalty")
        # m.addConstr((quicksum([quicksum([x[i, j] for j in range(26)]) for i in range(26)]) >= 1), name = "at least one roommate?!")

        m.addConstrs((quicksum([y[i, b] for b in range(8)]) == 1 - (1 - collectList[i]) for i in range(26)), name = "NPC has one biome unless uncollected")
        # m.addConstrs((x[i, i] == 0 for i in range(26)), name = "NPC can't be their own roommate")
        m.addConstrs((x[i, j] == x[j, i] for i in range(26) for j in range(26)), name = "roommates must be commutative")
        m.addConstrs((y[i, b] >= y[j, b] - (1 - x[i, j]) for i in range(26) for j in range(26) for b in range(8)), name = "roommates must share biome")
        m.addConstrs((x[j, k] >= x[i, j] - (1 - x[i, k]) for i in range(26) for j in range(26) for k in range(26)), name = "if i lives with j and k, j lives with k")
        m.addConstrs((quicksum([x[i, j] for j in range(26)]) <= 26 * collectList[i] for i in range(26)), name = "non-collected cannot have roommates")
        # m.addConstrs((quicksum([y[i, b] for b in range(8)]) <= 8 * collectList[i] for i in range(26)), name = "non-collected cannot have biomes")


        if self.pylonBox.isChecked:
            m.addConstrs((quicksum([y[i, b] for i in range(26)]) >= 1 for b in range(8)), name = "fill all pylon biomes")


        # %% define objective
        m.setObjective(         quicksum([     collectList[i] *   (0.1 + 0.9 * prioritizeList[i])        *   (1     +   0.05 * p[i]    +  quicksum([      NPCRelationMatrix[i][j] * x[i, j]                   for j in range(26)])           + quicksum([     NPCBiomeMatrix[i][b] * y[i, b]         for b in range(8)]))              for i in range(26)])   - 0.0001 * quicksum([quicksum([x[i, j] for i in range(26)]) for j in range(26)])   , GRB.MINIMIZE)
        # +  0.05 * quicksum([x[i, j] for j in range(26)])


        # %% perform optimization
        m.optimize()

        optimizedBiomesDict = {}
        try:
            accountedFor = [False] * 26
            for i in range(26):
                if not accountedFor[i]:
                    for b in range(8):
                        if abs(int(y[i, b].x)):
                            if b not in optimizedBiomesDict:
                                optimizedBiomesDict[b] = []

                            # print(f"{biomeDict[b]}: ", end="")
                    # print(f"y[{i},{b}] = " + str(abs(int(y[i, b].x))))
                            withi = []
                            for j in range(26):
                                if abs(int(x[i, j].x)):
                                    withi.append(j)
                                    accountedFor[j] = True
                            optimizedBiomesDict[b].append(withi)
            # print("\n")
                            # print(f"{NPCDict[i]} with {NPCDict[j]}.")
                        # print(f"x[{i},{j}] = " + str(abs(int(x[i, j].x))))


            # print("\nOptimal Value: %s" % (str(m.ObjVal)))
        except:
            self.error = QMessageBox()
            self.error.setText("Current setup is infeasible.")
            self.error.show()

        self.nextWindow = Optimized(optimizedBiomesDict)
        self.nextWindow.show()
        self.deleteLater()





class Optimized(QWidget):
    def __init__(self, optimizedBiomesDict):
        super().__init__()
        self.setWindowTitle("Optimized Setup")
        self.vbox = QVBoxLayout()
        self.setLayout(self.vbox)

        self.backButton = QPushButton("Back")

        self.grid = QGridLayout()

        self.backButton.clicked.connect(self.back)

        self.header = QLabel("Optimized Setup")
        self.header.setFont(QFont('Arial', 25))
        self.header.setAlignment(Qt.AlignCenter)
        self.vbox.addWidget(self.header)
        self.vbox.addLayout(self.grid)

        pprint(optimizedBiomesDict)

        i = 0
        for (biome, lists) in optimizedBiomesDict.items():
            picLabel = QLabel('picture')
            picLabel.setMinimumSize(24, 46)
            picLabel.setScaledContents(False)
            picPixmap = QPixmap()
            picPixmap.loadFromData(biomePics[biome])
            picLabel.setPixmap(picPixmap)
            self.grid.addWidget(picLabel, i, 0)

            for list in lists:
                j = 1
                for npc in list:
                    picLabel = QLabel('picture')
                    picLabel.setMinimumSize(24, 46)
                    picLabel.setScaledContents(False)
                    picPixmap = QPixmap()
                    picPixmap.loadFromData(NPCPics[npc])
                    picLabel.setPixmap(picPixmap)
                    self.grid.addWidget(picLabel, i, j)
                    j += 1
                i += 1



        for i in range(self.grid.columnCount()):
            self.grid.setColumnMinimumWidth(i, 70)
        for i in range(self.grid.rowCount()):
            self.grid.setRowMinimumHeight(i, 50)

        self.vbox.addWidget(self.backButton)
        # self.setMinimumSize(400, 800)

    def back(self):
        self.nextWindow = Home()
        self.nextWindow.show()
        self.deleteLater()

class QWrappedLabel(QLabel):
    def __init__(self, text):
        super().__init__(text)
        self.setWordWrap(True)


if __name__ == "__main__":

    NPCDict = {index: npc for (index, npc) in enumerate(['Guide', 'Merchant', 'Zoologist', 'Golfer',
                                                         'Nurse', 'Tavern-keep', 'Party Girl', 'Wizard', 'Demoli-tionist',
                                                         'Goblin Tinkerer', 'Clothier', 'Dye Trader', 'Arms Dealer',
                                                         'Steam-punker', 'Dryad', 'Painter', 'Witch Doctor', 'Stylist',
                                                         'Angler', 'Pirate', 'Mechanic', 'Tax Collector', 'Cyborg',
                                                         'Santa Claus', 'Truffle', 'Princess'])}

    NPCPics = {index: url for (index, url) in enumerate(['https://static.wikia.nocookie.net/terraria_gamepedia/images/7/7f/Guide.png/revision/latest/scale-to-width-down/26?cb=20191003231144', 'https://static.wikia.nocookie.net/terraria_gamepedia/images/1/19/Merchant.png/revision/latest/scale-to-width-down/30?cb=20161004000151', 'https://static.wikia.nocookie.net/terraria_gamepedia/images/6/61/Zoologist.png/revision/latest/scale-to-width-down/32?cb=20200516192903', 'https://static.wikia.nocookie.net/terraria_gamepedia/images/1/1a/Golfer.png/revision/latest/scale-to-width-down/32?cb=20200516183144',
                                                         'https://static.wikia.nocookie.net/terraria_gamepedia/images/c/cc/Nurse.png/revision/latest/scale-to-width-down/28?cb=20161005060102', 'https://static.wikia.nocookie.net/terraria_gamepedia/images/8/81/Tavernkeep.png/revision/latest/scale-to-width-down/32?cb=20161115191006', 'https://static.wikia.nocookie.net/terraria_gamepedia/images/a/a8/Party_Girl.png/revision/latest/scale-to-width-down/30?cb=20161130010012', 'https://static.wikia.nocookie.net/terraria_gamepedia/images/c/c7/Wizard.png/revision/latest/scale-to-width-down/34?cb=20151018113651', 'https://static.wikia.nocookie.net/terraria_gamepedia/images/6/6e/Demolitionist.png/revision/latest/scale-to-width-down/36?cb=20200330043525',
                                                         'https://static.wikia.nocookie.net/terraria_gamepedia/images/8/86/Goblin_Tinkerer.png/revision/latest/scale-to-width-down/24?cb=20150705070124', 'https://static.wikia.nocookie.net/terraria_gamepedia/images/d/d2/Clothier.png/revision/latest/scale-to-width-down/30?cb=20161009093143', 'https://static.wikia.nocookie.net/terraria_gamepedia/images/5/51/Dye_Trader.png/revision/latest/scale-to-width-down/24?cb=20161009093013', 'https://static.wikia.nocookie.net/terraria_gamepedia/images/9/9e/Arms_Dealer.png/revision/latest/scale-to-width-down/26?cb=20161004000744',
                                                         'https://static.wikia.nocookie.net/terraria_gamepedia/images/8/82/Steampunker.png/revision/latest/scale-to-width-down/22?cb=20200702150220', 'https://static.wikia.nocookie.net/terraria_gamepedia/images/5/5c/Dryad.png/revision/latest/scale-to-width-down/26?cb=20161004000507', 'https://static.wikia.nocookie.net/terraria_gamepedia/images/2/24/Painter.png/revision/latest/scale-to-width-down/34?cb=20150705103620', 'https://static.wikia.nocookie.net/terraria_gamepedia/images/a/ac/Witch_Doctor.png/revision/latest/scale-to-width-down/46?cb=20170108122024', 'https://static.wikia.nocookie.net/terraria_gamepedia/images/1/16/Stylist.png/revision/latest/scale-to-width-down/32?cb=20151031152652',
                                                         'https://static.wikia.nocookie.net/terraria_gamepedia/images/b/bf/Angler.png/revision/latest/scale-to-width-down/24?cb=20200702150720', 'https://static.wikia.nocookie.net/terraria_gamepedia/images/7/7d/Pirate.png/revision/latest/scale-to-width-down/26?cb=20170421220847', 'https://static.wikia.nocookie.net/terraria_gamepedia/images/5/55/Mechanic.png/revision/latest/scale-to-width-down/34?cb=20151018120500', 'https://static.wikia.nocookie.net/terraria_gamepedia/images/7/75/Tax_Collector.png/revision/latest/scale-to-width-down/34?cb=20150701011232', 'https://static.wikia.nocookie.net/terraria_gamepedia/images/a/a3/Cyborg.png/revision/latest/scale-to-width-down/24?cb=20161004001101',
                                                         'https://static.wikia.nocookie.net/terraria_gamepedia/images/5/58/Santa_Claus.png/revision/latest/scale-to-width-down/32?cb=20201013025452', 'https://static.wikia.nocookie.net/terraria_gamepedia/images/f/f2/Truffle.png/revision/latest/scale-to-width-down/30?cb=20200704192524', 'https://static.wikia.nocookie.net/terraria_gamepedia/images/f/f2/Princess.png/revision/latest/scale-to-width-down/30?cb=20201013172546'])}

    for (index, url) in NPCPics.items():
        try:
            NPCPics[index] = urllib.request.urlopen(url, timeout=15).read()
        except:
            print(f"Error reading picture for {NPCDict[index]}")

    biomeDict = {index: npc for (index, npc) in enumerate(['Forest', 'Underground', 'Desert', 'Ocean', 'Snow', 'Jungle',
                                                           'Hallow', 'Glowing Mushroom'])}

    biomePics = {index: url for (index, url) in enumerate(['https://static.wikia.nocookie.net/terraria_gamepedia/images/9/98/Forest_Pylon.png/revision/latest/scale-to-width-down/30?cb=20200516212639', 'https://static.wikia.nocookie.net/terraria_gamepedia/images/f/fe/Cavern_Pylon.png/revision/latest/scale-to-width-down/30?cb=20200516204135', 'https://static.wikia.nocookie.net/terraria_gamepedia/images/9/93/Desert_Pylon.png/revision/latest/scale-to-width-down/28?cb=20200516211330', 'https://static.wikia.nocookie.net/terraria_gamepedia/images/9/9e/Ocean_Pylon.png/revision/latest/scale-to-width-down/28?cb=20200516215943', 'https://static.wikia.nocookie.net/terraria_gamepedia/images/9/99/Snow_Pylon.png/revision/latest/scale-to-width-down/32?cb=20200516222105', 'https://static.wikia.nocookie.net/terraria_gamepedia/images/2/23/Jungle_Pylon.png/revision/latest/scale-to-width-down/32?cb=20200516214410',
                                                           'https://static.wikia.nocookie.net/terraria_gamepedia/images/d/d3/Hallow_Pylon.png/revision/latest/scale-to-width-down/28?cb=20200516213756', 'https://static.wikia.nocookie.net/terraria_gamepedia/images/e/e4/Mushroom_Pylon.png/revision/latest/scale-to-width-down/32?cb=20200516215542'])}

    for (index, url) in biomePics.items():
        try:
            biomePics[index] = urllib.request.urlopen(url, timeout=15).read()
        except:
            print(f"Error reading picture for {biomeDict[index]}")

    NPCRelationMatrix = []
    for i in range(26):
        NPCRelationMatrix.append([0 for i in range(26)])

    NPCBiomeMatrix = []
    for i in range(26):
        NPCBiomeMatrix.append([0 for i in range(8)])

    NPCRelationDict = {0: [[0], [3], [], [10, 2], [13], [15]],
                       1: [[0], [2], [], [3, 4], [21], [18]],
                       2: [[0], [2], [16], [3], [18], [12]],
                       3: [[0], [1], [18], [15, 2], [19], [1]],
                       4: [[6], [4], [12], [7], [14, 6], [2]],
                       5: [[6], [4], [8], [9], [0], [11]],
                       6: [[6], [1], [7, 2], [17], [1], [21]],
                       7: [[6], [3], [3], [1], [16], [22]],
                       8: [[1], [3], [5], [20], [12, 9], []],
                       9: [[1], [5], [20], [11], [10], [17]],
                       10: [[1], [6], [24], [21], [4], [20]],
                       11: [[2], [0], [], [12, 15], [13], [19]],
                       12: [[2], [4], [4], [13], [3], [8]],
                       13: [[2], [5], [22], [15], [14, 7, 6], []],
                       14: [[5], [2], [], [16, 24], [18], [3]],
                       15: [[5], [0], [14], [6], [24, 22], []],
                       16: [[5], [6], [], [14, 0], [4], [24]],
                       17: [[3], [4], [11], [19], [5], [9]],
                       18: [[3], [2], [], [8, 6, 21], [], [5]],
                       19: [[3], [1], [18], [5], [17], [0]],
                       20: [[4], [1], [9], [22], [12], [10]],
                       21: [[4], [6], [1], [6], [8, 20], [23]],
                       22: [[4], [5], [], [13, 20, 17], [2], [7]],
                       23: [[], [], [], [], [], [21]],
                       24: [[7], [], [0], [14], [10], [16]]}


    for (npc, lists) in NPCRelationDict.items():
        for biome in lists[0]:
            NPCBiomeMatrix[npc][biome] = -0.06
        for biome in lists[1]:
            NPCBiomeMatrix[npc][biome] = 0.06
        for other in lists[2]:
            NPCRelationMatrix[npc][other] = -0.12
        for other in lists[3]:
            NPCRelationMatrix[npc][other] = -0.06
        for other in lists[4]:
            NPCRelationMatrix[npc][other] = 0.06
        for other in lists[5]:
            NPCRelationMatrix[npc][other] = 0.12


    for i in range(26):
        NPCRelationMatrix[25][i] = -0.12
        NPCRelationMatrix[i][25] = 0
    NPCRelationMatrix[25][25] = 0
    NPCBiomeMatrix[23][4] = -0.12
    NPCBiomeMatrix[23][2] = 0.12






    app = QApplication(sys.argv)

    window = Home()
    window.show()

    sys.exit(app.exec_())

