import json, sys, os, time, os.path
from sys import exit

import pygame as pg

from LKobjs import *

import numpy as np
import pylibfreenect2
from pylibfreenect2 import Freenect2, SyncMultiFrameListener
from pylibfreenect2 import FrameType, Registration, Frame

#Press F for fullscreen and x to revert to windowed
#Adjust like 154 of LKobjs to increase or decrease hover time for button selection
#To run the system without the kinect, comment out everything in kinect initialization below AND
#set self.kinectActive on line 154 to False

##### KINECT INITIALIZATION #####
try:
    from pylibfreenect2 import OpenGLPacketPipeline
    pipeline = OpenGLPacketPipeline()
except:
    try:
        from pylibfreenect2 import OpenCLPacketPipeline
        pipeline = OpenCLPacketPipeline()
    except:
        from pylibfreenect2 import CpuPacketPipeline
        pipeline = CpuPacketPipeline()
print("Packet pipeline:", type(pipeline).__name__)
enable_depth = True
enable_rgb = True
fn = Freenect2()
num_devices = fn.enumerateDevices()
if num_devices == 0:
    print("No device connected!")
    sys.exit(1)

serial = fn.getDeviceSerialNumber(0)
device = fn.openDevice(serial, pipeline=pipeline)

types = 0

types |= FrameType.Color
types |= (FrameType.Ir | FrameType.Depth)
listener = SyncMultiFrameListener(types)

device.setColorFrameListener(listener)
device.setIrAndDepthFrameListener(listener)

device.start()

registration = Registration(device.getIrCameraParams(), device.getColorCameraParams())

undistorted = Frame(512, 424, 4)
registered = Frame(512, 424, 4)
##### END KINECT INITIALIZATION #####

#Returns a color between two other colors by __ percent
def lerp(colorFrom, colorTo, percent): 
    color = np.array(colorFrom)
    color2 = np.array(colorTo)
    vector = color2-color
    return color + vector * percent

#Take a value in a range and map it to the proportionate value in a new range
def mapTo(value, leftMin, leftMax, rightMin, rightMax):
    # Figure out how 'wide' each range is
    leftSpan = leftMax - leftMin
    rightSpan = rightMax - rightMin
    # Convert the left range into a 0-1 range (float)
    valueScaled = float(value - leftMin) / float(leftSpan)
    # Convert the 0-1 range into a value in the right range.
    return rightMin + (valueScaled * rightSpan)

def getNumRecipes():
    return len([name for name in os.listdir('./Recipes') if os.path.isfile(name)])

class PygameGame(object):

    def init(self):
        #Keep track of what screen we are working on
        self.screen = 'home'
        #keep track of what recipes are being looked at, when this changes, we load a new one
        self.recipeIndeces = {'app': None, 'entree': None, 'dessert': None} 
        #keep track of what step we are on in a recipe, when recipe changes this resets
        self.stepIndeces = {'app': None, 'entree': None, 'dessert': None}
        
        self.titlefont = pg.font.Font(os.path.abspath('Fonts/BalooThambi2-Medium.ttf'),100);
        self.h2font = pg.font.Font(os.path.abspath('Fonts/BalooThambi2-Medium.ttf'),70);
        self.subtitlefont = pg.font.Font(os.path.abspath('Fonts/BalooThambi2-Regular.ttf'),50);
        self.font = pg.font.Font(os.path.abspath('Fonts/BalooThambi2-Regular.ttf'),20);
        self.h3font = pg.font.Font(os.path.abspath('Fonts/BalooThambi2-Medium.ttf'),30);

        self.mainColor = (255,255,255)
        self.baseColor = (0,0,0)

        self.apps = []
        self.entrees = []
        self.desserts = []
        self.initRecipes()

        self.mouse = False

        self.homeInit()
        self.selectionInit()
        self.confirmInit()
        self.groceryInit()
        self.walkthroughInit()
        self.kinectInit()

        #diagnostics
        self.avgTime = 0
        self.timesCollected = 0
        self.totalTime = 0
        self.kinectActive = True

    def initRecipes(self):
        count = 0
        for file in os.listdir('./Recipes'):
            count += 1 
            filename = os.fsdecode(file)
            if filename.endswith(".json"): 
                with open('./Recipes/'+filename) as f:
                    recipe = json.load(f)
                    if 'appetizer' in recipe['tags']:
                        self.apps.append(recipe)
                    elif 'entree' in recipe['tags']:
                        self.entrees.append(recipe)
                    elif 'dessert' in recipe['tags']:
                        self.desserts.append(recipe)
                    print(recipe['title']+' loaded!')
        print('loaded ' + str(count) + ' recipes successfully...')

    def mousePressed(self, x, y):
        self.selecting = not self.selecting

    def mouseReleased(self, x, y):
        pass

    def mouseMotion(self, x, y):
        pass

    def mouseDrag(self, x, y):
        pass

    def keyPressed(self, keyCode, modifier):
        self.debugKeys()

    def keyReleased(self, keyCode, modifier):
        pass

    def debugKeys(self):
        if self.isKeyPressed(ord('m')): #Turns mouse into cursor
            self.mouse = not self.mouse
        elif self.isKeyPressed(ord('d')): #Shows what the depth camera sees
            self.debugDepth = not self.debugDepth
        elif self.isKeyPressed(ord('p')): #Go straight to confirmation screen
            self.loadDebugPreset()

    def mouseMode(self):
        self.cursorX = pg.mouse.get_pos()[0]
        self.cursorY = pg.mouse.get_pos()[1]

    def timerFired(self, dt):
        #Mouse mode
        if self.mouse:
            self.mouseMode()

        timeStart = time.time()
        if self.screen == 'home':
            self.homeTimerFired(dt)
        elif self.screen == 'selection':
            self.selectionTimerFired(dt)
        elif self.screen == 'confirm':
            self.confirmTimerFired(dt)
        elif self.screen == 'grocery':
            self.groceryTimerFired(dt)
        elif self.screen == 'walkthrough':
            self.walkthroughTimerFired(dt)
        
        if self.kinectActive:
            self.kinectTimerFired(dt)

        self.totalTime += time.time() - timeStart
        thisTime = time.time() - timeStart
        self.timesCollected += 1
        if self.timesCollected % 50 == 0: 
            print("Running at avg of " + str(self.totalTime / self.timesCollected) + " sec", " ("+str(thisTime)+" this time)")

    def redrawAll(self, screen):
        self.drawFrame(screen)
        if self.screen == 'home':
            self.homeDraw(screen)
        elif self.screen == 'selection':
            self.selectionDraw(screen)
        elif self.screen == 'confirm':
            self.confirmDraw(screen)
        elif self.screen == 'grocery':
            self.groceryDraw(screen)
        elif self.screen == 'walkthrough':
            self.walkthroughDraw(screen)

        if self.kinectActive:
            self.kinectDraw(screen)

    def isKeyPressed(self, key):
        return self._keys.get(key, False)

    def percentToAngle(self, percent):
        return mapTo(percent,0,1,0,330)

    def mouseConfirmLogic(self):
        if self.selectTimer >= 1:
            self.selecting = False
            self.confirmed = True
            self.selectTimer = 0

        if self.selecting:
            self.selectTimer += .33

        else:
            self.selectTimer = 0

    def mouseConfirmDraw(self,screen):
        if self.selecting:
            pg.gfxdraw.pie(screen, self.cursorX, self.cursorY, 20, 0, int(self.percentToAngle(self.selectTimer)), self.mainColor)

################################## HOME ########################################
    def homeInit(self):
        self.lerpCounter = 0
        self.lerpDir = 0
        self.selectTimer = 0
        self.selecting = False
        self.confirmed = False
        self.logo = pg.image.load("./Images/light_kitchen_blue.png")

    def tickLerp(self):
        if self.lerpDir == 0: #if counting up
            if self.lerpCounter < 1:
                self.lerpCounter += .01
            else:
                self.lerpDir = 1
        else:
            if self.lerpCounter > 0:
                self.lerpCounter -= .01
            else:
                self.lerpDir = 0

    def homeTimerFired(self, dt):
        self.mouseConfirmLogic()
        self.tickLerp()
        if self.confirmed:
            self.confirmed = False
            self.screen = 'selection'
            self.selecting = False

    def homeDraw(self,screen):
        fadeColor = lerp(self.mainColor,self.baseColor,self.lerpCounter)
        title = self.titlefont.render("Light Kitchen", True, self.mainColor)
        subtitle = self.subtitlefont.render("Tap to Begin", True, fadeColor)
        
        xDif = title.get_width()/2
        yDif = title.get_height()/2
        screen.blit(title,(self.width/2 - xDif,self.height/5-yDif))
        xDif = subtitle.get_width()/2
        yDif = subtitle.get_height()/2
        screen.blit(subtitle,(self.width/2 - xDif,4*self.height/5-yDif))
        self.mouseConfirmDraw(screen)
        screen.blit(self.logo,(self.width/2-self.logo.get_width()/2,self.height/2-self.logo.get_height()/2))

    def drawFrame(self,screen):
        color = self.mainColor
        if self.screen == 'home':
            color = lerp(self.mainColor,self.baseColor,self.lerpCounter)
        aa_round_rect(screen, (10,10,self.width-20,self.height-20), color, 30, 3, self.baseColor)


################################## SELE ########################################

    def selectionInit(self):
        self.appButtons = []
        self.entreeButtons = []
        self.dessertButtons = []
        self.populateRecipeButtons()
        self.filterButtons = []
        self.populateFilterButtons()
        self.selectOptionsButtons = []
        self.populateSOptionsButtons()

    def selectButtonsLogic(self):
        for button in self.selectOptionsButtons:
            if button.confirmed and button.text == 'Back to Home':
                self.screen = 'home'
                button.confirmed = False
            elif button.confirmed and button.text == 'Create a Recipe':
                button.confirmed = False
            elif button.confirmed and button.text == 'Meal Planning >':
                self.screen = 'confirm'
                button.confirmed = False

    def populateFilterButtons(self):
        buttonWidth = 200
        buttonHeight = 50
        filters = ["None","Vegetarian","Gluten Free","Dairy Free"]

        for i in range(len(filters)):
            self.filterButtons.append(Button((3+i*2)*self.width/13,6*self.height/8,buttonWidth,buttonHeight,filters[i]))

    def populateSOptionsButtons(self):
        font = pg.font.Font(os.path.abspath('Fonts/BalooThambi2-Medium.ttf'),30)
        col = (40,40,40)
        buttonWidth = 300
        buttonHeight = 75
        filters = ["Back to Home","Create Recipe","Get Planning!"]

        self.selectOptionsButtons.append(Button(self.width/6-50,7*self.height/8,buttonWidth,buttonHeight,"Back to Home",font,self.baseColor))
        self.selectOptionsButtons.append(Button(3*self.width/6,7*self.height/8,buttonWidth,buttonHeight,"Create a Recipe",font,self.baseColor))
        self.selectOptionsButtons.append(Button(5*self.width/6+50,7*self.height/8,buttonWidth,buttonHeight,"Meal Planning >",font,self.baseColor))

    def populateRecipeButtons(self):
        xMargin = 220
        buttonWidth = 400
        buttonHeight = 65

        for i in range(len(self.apps)):
            self.appButtons.append(RecipeButton(self.width/6, self.height/3+i*buttonHeight*1.25, buttonWidth, buttonHeight, self.apps[i]))
                            #change this
        for i in range(len(self.entrees)):                                                                     #and this
            self.entreeButtons.append(RecipeButton(3*self.width/6, self.height/3+i*buttonHeight*1.25, buttonWidth,buttonHeight, self.entrees[i]))

        for i in range(len(self.desserts)):
            self.dessertButtons.append(RecipeButton(5*self.width/6, self.height/3+i*buttonHeight*1.25, buttonWidth,buttonHeight, self.desserts[i]))

    def selectionTimerFired(self, dt):
        #Other buttons
        for button in self.selectOptionsButtons:
            button.selectAndConfirmLogic(self.cursorX,self.cursorY)
            if button.confirmed:
                self.selectButtonsLogic() 

        #Appetizers button functionality
        for i in range(len(self.appButtons)):
            if self.appButtons[i].confirmed and i != self.recipeIndeces['app']:
                if (self.recipeIndeces['app'] != None):
                    self.appButtons[self.recipeIndeces['app']].confirmed = False
                self.recipeIndeces['app'] = i
            self.appButtons[i].selectAndConfirmLogic(self.cursorX,self.cursorY)

        #Entrees
        for i in range(len(self.entreeButtons)):
            if self.entreeButtons[i].confirmed and i != self.recipeIndeces['entree']:
                if (self.recipeIndeces['entree'] != None):
                    self.entreeButtons[self.recipeIndeces['entree']].confirmed = False
                self.recipeIndeces['entree'] = i
            self.entreeButtons[i].selectAndConfirmLogic(self.cursorX,self.cursorY)

        #Desserts
        for i in range(len(self.dessertButtons)):
            if self.dessertButtons[i].confirmed and i != self.recipeIndeces['dessert']:
                if (self.recipeIndeces['dessert'] != None):
                    self.dessertButtons[self.recipeIndeces['dessert']].confirmed = False
                self.recipeIndeces['dessert'] = i
            self.dessertButtons[i].selectAndConfirmLogic(self.cursorX,self.cursorY)

    def selectionDraw(self, screen):
        #draw right to left so that tool tips draw on top
        for button in self.dessertButtons:
            button.draw(screen,self.cursorX,self.cursorY)
        for button in self.entreeButtons:
            button.draw(screen,self.cursorX,self.cursorY)
        for button in self.appButtons:
            button.draw(screen,self.cursorX,self.cursorY)
        for button in self.filterButtons:
            button.draw(screen,self.cursorX,self.cursorY)
        for button in self.selectOptionsButtons:
            button.draw(screen,self.cursorX,self.cursorY)

        title = self.h2font.render("Pick Your Recipes", True, self.mainColor)
        xDif = title.get_width()/2
        yDif = title.get_height()/2
        screen.blit(title,(self.width/2 - xDif, self.height/4-title.get_height()*1.5))

        title = self.subtitlefont.render("Appetizers", True, self.courseColors[0])
        xDif = title.get_width()/2
        yDif = title.get_height()/2
        screen.blit(title,(self.width/6 - xDif, self.height/3-title.get_height()*1.5))
        title = self.subtitlefont.render("Entrées", True, self.courseColors[1])
        xDif = title.get_width()/2
        yDif = title.get_height()/2
        screen.blit(title,(3*self.width/6 - xDif, self.height/3-title.get_height()*1.5))
        title = self.subtitlefont.render("Desserts", True, self.courseColors[2])
        xDif = title.get_width()/2
        yDif = title.get_height()/2
        screen.blit(title,(5*self.width/6 - xDif, self.height/3-title.get_height()*1.5))
        title = self.subtitlefont.render("Filters:", True, self.mainColor)
        xDif = title.get_width()/2
        yDif = title.get_height()/2
        screen.blit(title,(self.width/13 - xDif,6*self.height/8-yDif))

################################## CONF ########################################

    def confirmInit(self):
        self.confirmButtons = []
        self.totalActiveTime = self.getTotalActiveTime()
        self.populateConfirmButtons()

    def getTotalActiveTime(self):
        total = 0
        longestPassive = 0
        if self.recipeIndeces['app'] != None:
            total += self.appButtons[self.recipeIndeces['app']].activeTime
            for step in self.appButtons[self.recipeIndeces['app']].recipe['steps']:
                if step['passive_time'] > longestPassive:
                    longestPassive = step['passive_time']
        if self.recipeIndeces['entree'] != None:
            total += self.entreeButtons[self.recipeIndeces['entree']].activeTime
            for step in self.entreeButtons[self.recipeIndeces['entree']].recipe['steps']:
                if step['passive_time'] > longestPassive:
                    longestPassive = step['passive_time']
        if self.recipeIndeces['dessert'] != None:
            total += self.dessertButtons[self.recipeIndeces['dessert']].activeTime
            for step in self.dessertButtons[self.recipeIndeces['dessert']].recipe['steps']:
                if step['passive_time'] > longestPassive:
                    longestPassive = step['passive_time']

        return total + longestPassive

    def populateConfirmButtons(self):
        font = pg.font.Font(os.path.abspath('Fonts/BalooThambi2-Medium.ttf'),30)
        col = (40,40,40)
        buttonWidth = 300
        buttonHeight = 75

        self.confirmButtons.append(Button(self.width/6-50,7*self.height/8,buttonWidth,buttonHeight,"Back to Recipes",font,self.baseColor))
        self.confirmButtons.append(Button(3*self.width/6,7*self.height/8,buttonWidth,buttonHeight,"Grocery List",font,self.baseColor))
        self.confirmButtons.append(Button(5*self.width/6+50,7*self.height/8,buttonWidth,buttonHeight,"Get Cooking!",font,self.baseColor))

    def confirmTimerFired(self, dt):
        for button in self.confirmButtons:
            button.selectAndConfirmLogic(self.cursorX,self.cursorY)
            if button.confirmed:
                self.confirmButtonsLogic()

    def confirmDraw(self, screen):
        #Appetizer###############
        if self.recipeIndeces['app'] != None:
            recipeB = self.appButtons[self.recipeIndeces['app']]
            title = self.h3font.render(recipeB.text, True, self.courseColors[0])
            xDif = title.get_width()/2
            yDif = title.get_height()/2
            screen.blit(title,(self.width/6-xDif, self.height/6-2*yDif))    
            
            title = self.font.render('Time: '+ str(recipeB.totalTime)+" mins ("+str(recipeB.activeTime)+" active, "+str(recipeB.passiveTime)+" passive)", True, self.mainColor)
            xDif = title.get_width()/2
            yDif = title.get_height()/2
            screen.blit(title,(self.width/6-xDif, self.height/6+yDif))

            if "image" in recipeB.recipe:
                img = pg.image.load(recipeB.recipe['image'])
                xDif = img.get_width()//2
                yDif = img.get_height()//4
                screen.blit(img,(self.width/6-xDif, self.height/6+yDif))

            spaceDist = 11
            count = 0
            newLine = 0
            prevSpaces = 0
            for word in recipeB.recipe["description"].split(" "):
                count += 1
                if count % 5 == 0:
                    count = 0
                    newLine += 1
                    prevSpaces = 0
                title = self.font.render(word, True, self.mainColor)
                screen.blit(title,(self.width/18 + count*spaceDist + prevSpaces, 3.9*self.height/6+newLine*spaceDist*2))
                prevSpaces += title.get_width()

        #Entree###############
        if self.recipeIndeces['entree'] != None:
            recipeB = self.entreeButtons[self.recipeIndeces['entree']]
            #title
            title = self.h3font.render(self.entrees[self.recipeIndeces['entree']]['title'], True, self.courseColors[1])
            xDif = title.get_width()/2
            yDif = title.get_height()/2
            screen.blit(title,(3*self.width/6-xDif, self.height/6-2*yDif))
            #Timing
            title = self.font.render('Time: '+ str(recipeB.totalTime)+" mins ("+str(recipeB.activeTime)+" active, "+str(recipeB.passiveTime)+" passive)", True, self.mainColor)
            xDif = title.get_width()/2
            yDif = title.get_height()/2
            screen.blit(title,(3*self.width/6-xDif, self.height/6+yDif))

            if "image" in recipeB.recipe:
                img = pg.image.load(recipeB.recipe['image'])
                xDif = img.get_width()//2
                yDif = img.get_height()//4
                screen.blit(img,(6*self.width/12-xDif, self.height/6+yDif))

            spaceDist = 11
            count = 0
            newLine = 0
            prevSpaces = 0
            for word in recipeB.recipe["description"].split(" "):
                count += 1
                if count % 5 == 0:
                    count = 0
                    newLine += 1
                    prevSpaces = 0
                title = self.font.render(word, True, self.mainColor)
                screen.blit(title,(5.25*self.width/14 + count*spaceDist + prevSpaces, 3.9*self.height/6+newLine*spaceDist*2))
                prevSpaces += title.get_width()

        if self.recipeIndeces['dessert'] != None:
            recipeB = self.dessertButtons[self.recipeIndeces['dessert']]
            #title
            title = self.h3font.render(self.desserts[self.recipeIndeces['dessert']]['title'], True, self.courseColors[2])
            xDif = title.get_width()/2
            yDif = title.get_height()/2
            screen.blit(title,(5*self.width/6-xDif, self.height/6-2*yDif))

            #Timing
            title = self.font.render('Time: '+ str(recipeB.totalTime)+" mins ("+str(recipeB.activeTime)+" active, "+str(recipeB.passiveTime)+" passive)", True, self.mainColor)
            xDif = title.get_width()/2
            yDif = title.get_height()/2
            screen.blit(title,(5*self.width/6-xDif, self.height/6+yDif))

            if "image" in recipeB.recipe:
                img = pg.image.load(recipeB.recipe['image'])
                xDif = img.get_width()//2
                yDif = img.get_height()//4
                screen.blit(img,(10*self.width/12-xDif, self.height/6+yDif))

            spaceDist = 11
            count = 0
            newLine = 0
            prevSpaces = 0
            for word in recipeB.recipe["description"].split(" "):
                count += 1
                if count % 5 == 0:
                    count = 0
                    newLine += 1
                    prevSpaces = 0
                title = self.font.render(word, True, self.mainColor)
                screen.blit(title,(10.1*self.width/14 + count*spaceDist + prevSpaces, 3.9*self.height/6+newLine*spaceDist*2))
                prevSpaces += title.get_width()

        #General Timing
            title = self.h3font.render('Plan to start '+ str(self.getTotalActiveTime()) + " minutes ahead of time based on active time & longest passive time", True, self.mainColor)
            xDif = title.get_width()/2
            yDif = title.get_height()/2
            screen.blit(title,(self.width/2-xDif, 15+yDif))

        for button in self.confirmButtons:
            button.draw(screen,self.cursorX,self.cursorY)

    def confirmButtonsLogic(self):
        for button in self.confirmButtons:
            if button.confirmed and button.text == 'Back to Recipes':
                self.screen = 'selection'
                button.confirmed = False
            elif button.confirmed and button.text == 'Grocery List':
                self.screen = 'grocery'
                button.confirmed = False
            elif button.confirmed and button.text == 'Get Cooking!':
                self.populateSequenceList()
                self.populateControlButtons()
                self.screen = 'walkthrough'
                button.confirmed = False

################################## GROCERY ########################################
    def groceryInit(self):
        self.groceryButtons = []
        self.populateGroceryButtons()

    def populateGroceryButtons(self):
        font = pg.font.Font(os.path.abspath('Fonts/BalooThambi2-Medium.ttf'),30)
        col = (40,40,40)
        buttonWidth = 300
        buttonHeight = 75

        self.groceryButtons.append(Button(self.width/6-50,7*self.height/8,buttonWidth,buttonHeight,"Back to Overview",font,self.baseColor))
        self.groceryButtons.append(Button(3*self.width/6,7*self.height/8,buttonWidth,buttonHeight,"Send to Email",font,self.baseColor))
        self.groceryButtons.append(Button(5*self.width/6+50,7*self.height/8,buttonWidth,buttonHeight,"Get Cooking!",font,self.baseColor))


    def groceryTimerFired(self, dt):
        for button in self.groceryButtons:
            button.selectAndConfirmLogic(self.cursorX,self.cursorY)
            if button.confirmed:
                self.groceryButtonsLogic()

    def groceryButtonsLogic(self):
        for button in self.groceryButtons:
            if button.confirmed and button.text == 'Back to Overview':
                self.screen = 'confirm'
                button.confirmed = False
            elif button.confirmed and button.text == 'Send to Email':
                button.confirmed = False
            elif button.confirmed and button.text == 'Get Cooking!':
                self.populateSequenceList()
                self.populateControlButtons()

                self.screen = 'walkthrough'
                button.confirmed = False

    def groceryDraw(self, screen):
        #Buttons
        for button in self.groceryButtons:
            button.draw(screen,self.cursorX,self.cursorY)
        #title
        title = self.subtitlefont.render("Grocery List", True, self.mainColor)
        xDif = title.get_width()/2
        yDif = title.get_height()/2
        screen.blit(title,(self.width/2-xDif, self.height/6-2*yDif))
        #Ingredients
        ingredients, units = self.compileList()
        count = 0
        xCount = 0
        for ingredient in ingredients:

            count += 1
            if count % 10 == 0:
                xCount += 1 
                count = 1
            quant = ingredients[ingredient]
            if (quant % 1 == 0):
                quant = int(quant)
            plural = ''
            if quant > 1 and units[ingredient] != 'tsp' and units[ingredient] != 'tbsp' and units[ingredient] != 'whole': #not applicabble to tsp tbsp whole
                plural = 's'
            prepIng = " ".join(ingredient.split("_")).capitalize()
            title = self.h3font.render(" - "+ prepIng+': '+str(quant) + " "+units[ingredient]+plural, True, self.mainColor)
            xDif = title.get_width()/2
            yDif = title.get_height()/2
            screen.blit(title,(self.width/8+400*xCount, self.height/7+2*yDif*count))

    def compileList(self):
        ingredients = dict()
        units = dict()
        recipes = []
        if self.recipeIndeces['app'] != None:
            recipes.append(self.apps[self.recipeIndeces['app']])
        if self.recipeIndeces['entree'] != None:
            recipes.append(self.entrees[self.recipeIndeces['entree']])
        if self.recipeIndeces['dessert'] != None:
            recipes.append(self.desserts[self.recipeIndeces['dessert']])

        for recipe in recipes:
            for step in recipe['steps']:
                for ingredient in step['ingredients']:
                    name = ingredient.split()[0]
                    quant = float(ingredient.split()[1])
                    unit = ingredient.split()[2]
                    
                    if name in ingredients: 
                        ingredients[name] += quant
                    else:
                        ingredients[name] = quant

                    if name not in units:
                        units[name] = unit
        return (ingredients,units)

################################## WALKTHROUGH ########################################

    #returns the total time of a recipe through a given step
    def activeSumTimeToStep(self, steps, stepIndex):
        total = 0
        for i in range(0,stepIndex): #non inclusive so add 1
            if steps[i][0] == steps[stepIndex][0]: #if we're looking at the right course
                total += steps[i][2]
        return total

    # 0 = App, 1 = Entree, 2 = Dessert
    #returns a list of the ordered steps
    #Function is called when changing to the walkthrough screen
    #returns [course index, recipe, step index, instruction index, completed T/F]
    def populateSequenceList(self):
        self.courseToRecipe = {0:self.apps[self.recipeIndeces['app']],2:self.desserts[self.recipeIndeces['dessert']],1:self.entrees[self.recipeIndeces['entree']]}
        self.walkthroughIndex = 0
        result = []

        if self.recipeIndeces['dessert'] != None:
            for i in range(len(self.desserts[self.recipeIndeces['dessert']]['steps'])):
                #print(self.desserts[self.recipeIndeces['dessert']]['steps'][i]['name'])
                for j in range(len(self.desserts[self.recipeIndeces['dessert']]['steps'][i]['instructions'])):
                    result.append((2,self.desserts[self.recipeIndeces['dessert']],i,j,False))
        if self.recipeIndeces['app'] != None:
            for i in range(len(self.apps[self.recipeIndeces['app']]['steps'])):
                for j in range(len(self.apps[self.recipeIndeces['app']]['steps'][i]['instructions'])):
                    result.append((0,self.apps[self.recipeIndeces['app']],i,j,False))
        if self.recipeIndeces['entree'] != None:
            for i in range(len(self.entrees[self.recipeIndeces['entree']]['steps'])):
                for j in range(len(self.entrees[self.recipeIndeces['entree']]['steps'][i]['instructions'])):
                    result.append((1,self.entrees[self.recipeIndeces['entree']],i,j,False))

        self.walkthroughSequence = result
        self.optimalOrderCalculation()
        self.refreshStepDetails()
        self.refreshTimers()
        
        
    #if the active time to the next passive time is less than the longest passive time, go to the steps to get to the next longest
    #[course, step, atime, ptime] ------ then can know who has the longest passive time
    def createTimeSteps(self):
        optimizationList = []
        for i in range(len(self.walkthroughSequence)):
                #print(self.walkthroughSequence[i][3])
            if self.walkthroughSequence[i][3] == 0: #if it's a new step (0th instruction)
                atime = self.walkthroughSequence[i][1]['steps'][self.walkthroughSequence[i][2]]['active_time']
                ptime = self.walkthroughSequence[i][1]['steps'][self.walkthroughSequence[i][2]]['passive_time']
                optimizationList.append([self.walkthroughSequence[i][0],self.walkthroughSequence[i][2],atime,ptime])
        return optimizationList

    def optimalOrderCalculation(self):
        optiList = self.createTimeSteps()
        longestPassive = 0
        secondLongestPassive = 0
        for i in range(len(optiList)):
            if optiList[i][3] > optiList[secondLongestPassive][3]:
                secondLongestPassive = i
                if optiList[secondLongestPassive][3] > optiList[longestPassive][3]: #switch 1st and 2nd
                    temp = longestPassive
                    longestPassive = secondLongestPassive
                    secondLongestPassive = temp
        
        firstCourse,longestStep = optiList[longestPassive][0],optiList[longestPassive][1]
        secondCourse,secondLongestStep = optiList[secondLongestPassive][0],optiList[secondLongestPassive][1]
        thirdCourse = {0,1,2}.difference({firstCourse,secondCourse}).pop()
        print('Order: ',firstCourse,secondCourse,thirdCourse)
        print('longests ',optiList[longestPassive][3],optiList[secondLongestPassive][3])
        print('longest Step: ',optiList[longestPassive])
        lastLast = 0
        for i in range(len(optiList)):
            if optiList[i][0] == thirdCourse:
                lastLast = i

        thirdCourseTotalTime = self.activeSumTimeToStep(optiList,lastLast)
    
        #Add the sequence up to the longest step
        order = [firstCourse,secondCourse,thirdCourse] #course numbers in order
        index = 0
        for i in range(len(optiList)): #find the starting point
            if optiList[i][0] == order[0]:
                index = i
                break
        leftOff = {0:0,1:0,2:0} #list of courses and their last index written to
        courseIndex = 0
        nextPassive = longestStep + 1
        optiSequence = []
        while leftOff[0] != -1 or leftOff[1] != -1 or leftOff[2] != -1:
            
            #Put the current course from leftOff to nextPassive in
            course = order[courseIndex]

            print(course,leftOff[course],nextPassive)
            if leftOff[course] != -1:
                optiSequence = optiSequence + self.generateSequenceToStep(course,leftOff[course],nextPassive)

                #Record that we went there in that course
                leftOff[course] = nextPassive
            #Go to next course
            courseIndex = (courseIndex + 1) % 3
            #print(courseIndex)
            course = order[courseIndex]
            #Get that courses nextPassive
            nextPassive = self.getNextPassive(course,leftOff[course])       

        self.walkthroughSequence = optiSequence

    def getNextPassive(self,course,startIndex):
        recipeSteps = self.courseToRecipe[course]['steps']
        for i in range(startIndex+1,len(recipeSteps)):
            if recipeSteps[i]['passive_time'] != 0:
                return i+1
        return -1

    def generateSequenceToStep(self,course,stepFrom,stepTo):
        result = []
        if stepTo == -1:
            stepTo = len(self.courseToRecipe[course]['steps'])

        for i in range(stepFrom,stepTo):#len(self.courseToRecipe[course]['steps'])):
             for j in range(len(self.courseToRecipe[course]['steps'][i]['instructions'])):
                result.append((course,self.courseToRecipe[course],i,j,False))
        return result


    def walkthroughInit(self):
        self.walkthroughSequence = []
        self.courseToRecipe = dict()
        self.walkthroughIndex = 0
        self.smartOrderActive = False
        self.stepTitle = ''
        self.stepIngredients = ''
        self.stepTiming = ''
        self.stepInstructions = ''
        self.walkh1 = pg.font.Font(os.path.abspath('Fonts/BalooThambi2-Medium.ttf'),43);
        self.walkh2 = pg.font.Font(os.path.abspath('Fonts/BalooThambi2-Medium.ttf'),33);
        self.walkreg = pg.font.Font(os.path.abspath('Fonts/BalooThambi2-Regular.ttf'),30);
        self.walksmall = pg.font.Font(os.path.abspath('Fonts/BalooThambi2-Regular.ttf'),25);
        self.debugPreset = False

        self.controlButtons = []
        self.populateControlButtons()
        self.activeTimers = []
        self.passiveTimers = []
        self.timers = []
        self.courseColors = {0:(50,50,255),1:(255,50,50),2:(255,50,255)}
        self.optimize = True

    def populateTestTimers(self):
        self.timers.append(Timer('Prep the hardware!',0,1/10*self.height,6*self.width//36,120))

    def loadDebugPreset(self):
        self.recipeIndeces['app'] = 0
        self.recipeIndeces['entree'] = 0
        self.recipeIndeces['dessert'] = 0
        self.screen = 'confirm'

    def numToCourse(self,index):
        return ['app','entree','dessert'][index]

    def onStepChange(self):
        self.refreshStepDetails()
        self.refreshTimers()

    def findIndexOfRecipe(self,targ):
        #Find the current step of that recipe
        for i in range(len(self.walkthroughSequence)):
            #If it's incomplete and of the target course
            if self.walkthroughSequence[i][4] == False and self.walkthroughSequence[i][0] == targ:
                #print(self.walkthroughSequence[i])
                return i
        #print("nothing found")
        return self.walkthroughIndex

    def populateControlButtons(self):
        #wipe
        self.controlButtons = []
        #Instruction buttons
        font = pg.font.Font(os.path.abspath('Fonts/BalooThambi2-Bold.ttf'),50)
        col = (40,40,40)
        buttonWidth = 300
        buttonHeight = 75
        #Step buttons
        self.controlButtons.append(Button(34.5*self.width/36-5,8*self.height/10,3/36*self.width-20,self.height/10,"<",font,self.baseColor,1))
        self.controlButtons.append(Button(34.5*self.width/36-5,9*self.height/10,3/36*self.width-20,self.height/10,">",font,self.baseColor,1))
        #icon buttons
        self.controlButtons.append(IconButton(34.5*self.width/36-5,self.height/10,3/36*self.width-20,self.height/10,"exit",font,self.baseColor,1,'./Images/exit.png'))
        self.controlButtons.append(IconButton(34.5*self.width/36-5,2*self.height/10,3/36*self.width-20,self.height/10,"info",font,self.baseColor,1,'./Images/info.png'))
        if self.recipeIndeces['app'] != None:
            self.controlButtons.append(IconButton(34.5*self.width/36-5,3.75*self.height/10,3/36*self.width-20,self.height/10,"app",font,self.baseColor,1,'./Images/app.png'))
        if self.recipeIndeces['entree'] != None:
            self.controlButtons.append(IconButton(34.5*self.width/36-5,5*self.height/10,3/36*self.width-20,self.height/10,"entree",font,self.baseColor,1,'./Images/entree.png'))
        if self.recipeIndeces['dessert'] != None:
            self.controlButtons.append(IconButton(34.5*self.width/36-5,6.25*self.height/10,3/36*self.width-20,self.height/10,"dessert",font,self.baseColor,1,'./Images/dessert.png'))

    def markStepComplete(self):
        (course,recipe,step,instruction,completed) = self.walkthroughSequence[self.walkthroughIndex]
        self.walkthroughSequence[self.walkthroughIndex] = (course,recipe,step,instruction,True)

    def markStepIncomplete(self):
        (course,recipe,step,instruction,completed) = self.walkthroughSequence[self.walkthroughIndex]
        self.walkthroughSequence[self.walkthroughIndex] = (course,recipe,step,instruction,False)

    def controlButtonsLogic(self):
        for button in self.controlButtons:
            if button.confirmed and button.text == '<':
                #only allowed if greater than 0
                if self.walkthroughIndex > 0:
                    self.walkthroughIndex -= 1 
                    self.markStepIncomplete()
                    self.onStepChange()
                button.confirmed = False
            elif button.confirmed and button.text == '>':
                #The list of walkthrough indeces takes care of recipe switching as it carries instruction, step, and recipe info
                if self.walkthroughIndex < len(self.walkthroughSequence)-1:
                    self.markStepComplete()
                    self.walkthroughIndex += 1 
                    self.onStepChange()
                    #print('yes '+str(self.walkthroughIndex))
                if self.walkthroughIndex == len(self.walkthroughSequence):
                    self.screen = 'finish'
                button.confirmed = False

            #Course Change Buttons
            elif button.confirmed and button.text == 'app':
                #change the index to that of the earliest appetizer recipe
                self.walkthroughIndex = self.findIndexOfRecipe(0)
                #refresh the content with the new stuff
                self.refreshStepDetails()
                button.confirmed = False
            elif button.confirmed and button.text == 'entree':
                #change the index to that of the earliest appetizer recipe
                self.walkthroughIndex = self.findIndexOfRecipe(1)
                #refresh the content with the new stuff
                self.refreshStepDetails()
                button.confirmed = False
            elif button.confirmed and button.text == 'dessert':
                #change the index to that of the earliest appetizer recipe
                self.walkthroughIndex = self.findIndexOfRecipe(2)
                #refresh the content with the new stuff
                self.refreshStepDetails()
                button.confirmed = False

            elif button.confirmed and button.text == 'exit':
                self.screen = 'confirm'
                button.confirmed = False

    def refreshStepDetails(self):
        recipe = self.walkthroughSequence[self.walkthroughIndex][1]
        step = recipe['steps'][self.walkthroughSequence[self.walkthroughIndex][2]]
        self.recipeTitle = recipe['title']
        self.stepTitle = step['name']
        self.stepIngredients = (",").join(step['ingredients'])
        self.stepTiming = "Active time: " + str(step['active_time']) + " min, Passive time: " + str(step['passive_time']) + " min"
        self.stepInstructions = step['instructions'][self.walkthroughSequence[self.walkthroughIndex][3]]

    def refreshTimers(self):
        #every time we hit a new step we want to start active and passive timers, as well as wipe all of the active timers
        #dont create any timers if the time is 0
        #append active timers to the front so that we can pop them
        #Wipe active timers if it's a new step
        
        #delete any passive timers that are done

        #if we're on a new step
        if self.walkthroughSequence[self.walkthroughIndex][3] == 0: 
            self.activeTimers = []
            #If the active time doesnt = 0
            title = self.walkthroughSequence[self.walkthroughIndex][1]['steps'][self.walkthroughSequence[self.walkthroughIndex][2]]['name']
            atime = self.walkthroughSequence[self.walkthroughIndex][1]['steps'][self.walkthroughSequence[self.walkthroughIndex][2]]['active_time']
            ptime = self.walkthroughSequence[self.walkthroughIndex][1]['steps'][self.walkthroughSequence[self.walkthroughIndex][2]]['passive_time']
            course = self.walkthroughSequence[self.walkthroughIndex][0]
            if atime != 0:
                self.activeTimers.append(Timer(title,10,0,6*self.width//36-10,atime,lerp(self.courseColors[course],(0,0,0),.5)))
            if ptime != 0:
                self.passiveTimers.append(Timer(title,10,0,6*self.width//36-10,ptime,lerp(self.courseColors[course],(0,0,0),.65),False))

        self.timers = self.activeTimers + self.passiveTimers
        for i in range(len(self.timers)):
            self.timers[i].y = 2*self.height//10 + self.timers[i].height*i - 10

    def timerButtonsLogic(self):
        for timer in self.timers:
            timer.tickTimer(self.cursorX,self.cursorY)

            if timer.cancelButton.confirmed:
                self.timers.pop(self.timers.index(timer))

            elif timer.pauseButton.confirmed:
                timer.togglePause()
                timer.pauseButton.confirmed = False

            elif timer.addTimeButton.confirmed:
                timer.addTime(5)
                timer.addTimeButton.confirmed = False

    def walkthroughTimerFired(self,dt):
        #step buttons
        for button in self.controlButtons:
            button.selectAndConfirmLogic(self.cursorX,self.cursorY)
            if button.confirmed:
                self.controlButtonsLogic()
        #timers
        self.timerButtonsLogic()
            


    def drawTimerSection(self, screen):
        #Timer title text
        title = self.walkh1.render('Timers', True, self.mainColor)
        xDif = title.get_width()/2
        yDif = title.get_height()/2
        screen.blit(title,(self.width*3/36-xDif, 1/10*self.height-yDif))
        #timer line
        pg.draw.line(screen,self.mainColor,(6/36*self.width,10),(6/36*self.width,self.height-10),3)

    def drawStepsSection(self, screen):
        #steps line
        pg.draw.line(screen,self.mainColor,(33/36*self.width,10),(33/36*self.width,self.height-10),3)

    def drawIngredients(self,screen):
        bump = 0
        ingrds = 0
        previousSpace = 0
        #Ingredients
        for i in range(len(self.stepIngredients.split(","))):
            ingrds += 1
            if i % 4 == 0:
                bump += 1 
                previousSpace = 0
                ingrds = 0

            ingredient = self.stepIngredients.split(",")[i].split(' ')[0]
            quant = self.stepIngredients.split(",")[i].split(' ')[1]
            unit = self.stepIngredients.split(",")[i].split(' ')[2]
            s = ''
            if '_' in ingredient:
                ingredient = (' ').join(ingredient.split('_'))
            if float(quant) > 1 and (unit != 'whole' or unit != 'tbsp' or unit != 'tsp'):
                s = 's'
            text = self.walksmall.render('- '+quant +' '+ unit.capitalize() + s + ' '+ ingredient.capitalize() , True, self.mainColor)
            screen.blit(text,(self.width*8/36 + previousSpace + 12*ingrds, 2.15/10*self.height + text.get_height()*bump))
            previousSpace += text.get_width()

    def drawProgress(self,screen):
        #shaded circles for done
        #empty circles for not done
        #filled circle for working on
        #[course index, recipe, step index, instruction index, completed T/F]
        startingRecipe = self.walkthroughSequence[self.walkthroughIndex][1]
        startingCourse = self.walkthroughSequence[self.walkthroughIndex][0]
        minIndex = max(0,self.walkthroughIndex-5)
        maxIndex = min(self.walkthroughIndex+5,len(self.walkthroughSequence))

        appColor = (255,150,150)
        entreeColor = (150,255,150)
        dessertColor = (150,150,255)
        size = 0
        color = (0,0,0)
        stroke = 0
        startX = 13 * self.width//36
        constY = int(9.2*self.height/10)
        numDrawn = 0
        spacing = 45
        for i in range(minIndex,maxIndex):
            numDrawn += 1
            #size - new step means instruction will be 0
            if self.walkthroughSequence[i][3] == 0: #first isntruction of step
                size = 20
            else:
                size = 10
            #color (course & completed lerp)
            #Course
            color = self.courseColors[self.walkthroughSequence[i][0]]
            #Completed
            if self.walkthroughSequence[i][4] == True:
               color = lerp(color,(0,0,0),.6)
            elif not self.walkthroughSequence[i][4] and i != self.walkthroughIndex: #if its incomplete and not the one we're on
                stroke = 2 
            if stroke == 0:
                pg.gfxdraw.filled_circle(screen,startX + (spacing*numDrawn),constY,size,color)
            pg.gfxdraw.aacircle(screen,startX + (spacing*numDrawn),constY,size,color)
            

    def drawStepInstructionWords(self, screen):
        words = self.stepInstructions.split(" ")
        count = 0
        bump = 0
        previousSpace = 0 
        for i in range(len(words)):
            if count == 0 and bump == 0:
                words[i] = words[i].capitalize()
            count += 1
            if count % 12 == 0:
                count = 0
                bump += 1
                previousSpace = 0
            text = self.walkreg.render(words[i], True, self.mainColor)
            screen.blit(text,(self.width*8/36 + previousSpace + 8*count, 4/10*self.height + text.get_height()*bump))
            previousSpace += text.get_width()


    def drawStepInstructions(self, screen):
        #Recipe title
        title = self.walkh1.render(self.recipeTitle, True, self.mainColor)
        screen.blit(title,(self.width*8/36, 1/10*self.height))
        #Step title
        title = self.walkh2.render(self.stepTitle, True, self.mainColor)
        screen.blit(title,(self.width*8/36, 2/10*self.height))
        #Step timing
        title = self.walksmall.render(self.stepTiming, True, self.mainColor)
        screen.blit(title,(self.width*19.5/36, 2/10*self.height+3))

        if self.stepIngredients != '':
            self.drawIngredients(screen)
        if self.stepInstructions != '':
            self.drawStepInstructionWords(screen)

    def walkthroughDraw(self, screen):
        self.drawTimerSection(screen)
        self.drawStepsSection(screen)
        self.drawStepInstructions(screen)
        self.drawProgress(screen)

        for button in self.controlButtons:
            button.draw(screen,self.cursorX,self.cursorY)
        for timer in self.timers:
            timer.draw(screen,self.cursorX,self.cursorY)
############################# KINECT FUNCTIONS #################################
    def kinectInit(self):
        #KINECT VARIABLES
        self.xyzrgb = None
        self.frame = [[]]
        self.kinectDelay = 0
        self.avgDepth = 0
        self.avgColor = (0,0,0)
        self.counted = 0
        self.depthTolerance = 0
        self.colorTolerance = 0
        self.moveRight = 75
        self.highestY = len(self.frame[0])
        self.highestX = 0
        self.rightBound = 100 #Right bound higher number pushes left
        self.leftBound = self.rightBound + 335
        self.topBound = 75 #right bound higher goes further left
        self.bottomBound = self.topBound + 185
        self.calibrated = False
        self.debugDepth = False
        self.scale = 4
        self.yTransform = -self.topBound*self.scale
        self.xTransform = -self.rightBound*self.scale
        self.cursorX, self.cursorY = 0,0
    
    def updateFrame(self,screen):
        highestY = 511
        highestX = 0
        lastAvgDepth = self.avgDepth
        lastAvgColor = self.avgColor

        self.counted = 0
        self.avgColor = (0,0,0)

        frames = listener.waitForNewFrame()

        color = frames["color"]
        ir = frames["ir"]
        depth = frames["depth"]

        registration.apply(color, depth, undistorted, registered)
        listener.release(frames)

        frame = []
        for row in range(512):
            line = []
            for col in range(424):
                #coordinate, depth, color
                if registration.getPointXYZRGB(undistorted,registered,col,row)[-1] != 0:
                    x, y, z, b, g, r = registration.getPointXYZRGB(undistorted,registered,col,row)

                    deep = mapTo(z,-1,1,0,4) #<------ defining depth range

                    self.avgDepth += deep
                    self.addAvgColor(r,g,b)
                    self.counted += 1

                    if self.rightBound < row < self.leftBound and self.topBound < col < self.bottomBound and abs(deep - lastAvgDepth) > self.depthTolerance and self.difInColor((r,g,b),lastAvgColor) > self.colorTolerance:
                        if col < highestY:
                            highestY = col
                            highestX = row
                            r,g,b = (0,255,0)

                        if self.debugDepth:
                            pg.draw.circle(screen,(r,g,b),(int(row*self.scale+self.xTransform),int(col*self.scale+self.yTransform)),3)

                    if self.debugDepth:
                        if self.rightBound == row or row == self.leftBound:
                            r,g,b = (200,200,200)
                        elif self.topBound == col or col == self.bottomBound:
                            r,g,b = (100,100,100)
                        
                        pg.draw.circle(screen,(r,g,b),(int(row*self.scale+self.xTransform),int(col*self.scale+self.yTransform)),3)
                else:
                    x = 0
                    y = 0
                    deep = 0
                    r,g,b = (0,0,0)

                line.append([(int(row*self.scale + self.xTransform),int(col*self.scale+self.yTransform)),int(deep),(r,g,b)])

            frame.append(line)

        self.frame = frame
        self.calcAvgColor()
        self.avgDepth /= self.counted
        self.highestY = highestY
        self.highestX = highestX

    def addAvgColor(self,r1,g1,b1):
        r,g,b = self.avgColor
        self.avgColor = (r+r1, g+g1, b+b1)

    def calcAvgColor(self):
        r,g,b = self.avgColor
        self.avgColor = (r//self.counted,g//self.counted,b//self.counted)

    def difInColor(self,color,color1):
        #using euclidian distance
        r,b,g = color
        r1,b1,g1 = color1
        dr = abs(r-r1)
        dg = abs(g-g1)
        db = abs(b-b1)

        return max([dr,dg,db])#( (r-r1)**2 + (g-g1)**2 + (b-b1)**2 )**(1/2)

    def calibrateFilters(self):
        #Loop through adding small increments to self.depthTolerance and self.colorTolerance until the bounding box shows nothing but the two colors
        allGood = True

        for x in range(len(self.frame)):
            for y in range(len(self.frame[0])):
                coords = self.frame[x][y][0]
                depth = self.frame[x][y][1]
                color = self.frame[x][y][2]

                if self.rightBound < y < self.leftBound and self.topBound < x < self.bottomBound and self.difInColor(color,self.avgColor) > self.colorTolerance and abs(depth - self.avgDepth) > self.depthTolerance and color != (0,0,0):
                    self.depthTolerance += .05
                    self.colorTolerance += 1
                    allGood = False

        print("Calibrated to: ", self.colorTolerance,self.depthTolerance)
        self.calibrated = allGood

    def kinectTimerFired(self,dt):
        self.cursorX, self.cursorY = ((512*self.scale-self.highestX*self.scale)+self.xTransform, self.highestY*self.scale+self.yTransform)
        if self.kinectDelay < 5:
            self.kinectDelay += 1
        else:
            if not self.calibrated:
                self.calibrateFilters()

    def kinectDraw(self,screen):
        self.updateFrame(screen) #BREAKS MVP updates and draws at the same time to boost efficiency 4x
        pg.draw.circle(screen,(255,0,255),(self.cursorX,self.cursorY),35,2)

################################## PYGAME LOOP (Template by lukas peraz) #######
    #projector is 1366 x 768
    def __init__(self, width=1366, height=768, fps=100, title="Light Kitchen"):
        self.width = width
        self.height = height
        self.fps = fps
        self.title = title
        self.bgColor = (0, 0, 0)
        pg.init()

    def run(self):

        clock = pg.time.Clock()
        screen = pg.display.set_mode((self.width,self.height))
        # set the title of the window
        pg.display.set_caption(self.title)

        # stores all the keys currently being held down
        self._keys = dict()

        # call game-specific initialization
        self.init()
        playing = True
        while playing:
            time = clock.tick(self.fps)
            self.timerFired(time)
            for event in pg.event.get():
                if event.type == pg.MOUSEBUTTONDOWN and event.button == 1:
                    self.mousePressed(*(event.pos))
                elif event.type == pg.MOUSEBUTTONUP and event.button == 1:
                    self.mouseReleased(*(event.pos))
                elif (event.type == pg.MOUSEMOTION and
                      event.buttons == (0, 0, 0)):
                    self.mouseMotion(*(event.pos))
                elif (event.type == pg.MOUSEMOTION and
                      event.buttons[0] == 1):
                    self.mouseDrag(*(event.pos))
                elif event.type == pg.KEYDOWN:
                    self._keys[event.key] = True
                    self.keyPressed(event.key, event.mod)
                    if event.key == ord("q"):
                        playing = False
                    if event.key == ord('f'):
                        pg.display.set_mode((self.width,self.height), pg.FULLSCREEN)
                    if event.key == ord('x'):
                        pg.display.set_mode((self.width,self.height))
                elif event.type == pg.KEYUP:
                    self._keys[event.key] = False
                    self.keyReleased(event.key, event.mod)
                elif event.type == pg.QUIT:
                    playing = False
            screen.fill(self.bgColor)
            self.redrawAll(screen)
            pg.display.flip()

        pg.quit() 

def main():
    game = PygameGame()
    game.run()

if __name__ == '__main__':
    main()
