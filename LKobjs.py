import json, sys, os, time, random
import pygame as pg
import numpy as np

from pygame import gfxdraw

def lerp(colorFrom, colorTo, percent): 
    color = np.array(colorFrom)
    color2 = np.array(colorTo)
    vector = color2-color
    return color + vector * percent

def mapTo(value, leftMin, leftMax, rightMin, rightMax):
    # Figure out how 'wide' each range is
    leftSpan = leftMax - leftMin
    rightSpan = rightMax - rightMin
    # Convert the left range into a 0-1 range (float)
    valueScaled = float(value - leftMin) / float(leftSpan)
    # Convert the 0-1 range into a value in the right range.
    return rightMin + (valueScaled * rightSpan)

class Timer:
    def __init__(self,title,x,y,width,totalTime, bgCol = (0,0,0), on = True):
        self.on = on
        self.done = False
        self.title = title
        self.x = x
        self.oldY = y
        self.y = y
        self.width = width
        self.height = 150
        self.buttonWidth = -7 + self.width//3
        self.buttonHeight = 50
        self.buttonY = self.y+1.75*self.height//3
        self.totalTime = totalTime * 60 #in convert from minutes to seconds
        self.remainingTime = self.totalTime
        self.initTime = time.time()
        self.additional = 0
        self.mainColor = (255,255,255)
        self.bgCol = bgCol
        self.titlefont = pg.font.Font(os.path.abspath('Fonts/BalooThambi2-Regular.ttf'),20);
        self.timefont = pg.font.Font(os.path.abspath('Fonts/BalooThambi2-Medium.ttf'),30);
        self.playPath = "./Images/play.png"
        self.pausePath = "./Images/pause.png"
        pic = self.pausePath
        if not on:
            pic = self.playPath
        self.cancelButton = IconButton((self.x+self.width//2)-(3*self.buttonWidth//2)-5,self.buttonY,self.buttonWidth,self.buttonHeight,"cancel",self.titlefont,self.bgCol,1,'./Images/cancel.png')
        self.pauseButton = IconButton((self.x+self.width//2)-self.buttonWidth//2+12,self.buttonY,self.buttonWidth,self.buttonHeight,"pause",self.titlefont,self.bgCol,1,pic)
        self.addTimeButton = IconButton((self.x+self.width//2)+(self.buttonWidth//2)+5,self.buttonY,self.buttonWidth,self.buttonHeight,"add time",self.titlefont,self.bgCol,1,'./Images/add_time.png')

    def tickTimer(self,cursorX,cursorY):
        if self.y != self.oldY:
            self.buttonY = self.y+1.75*self.height//3
            self.cancelButton.y = self.buttonY + self.buttonHeight//2# + self.cancelButton.img.get_height()
            self.cancelButton.x += 3*self.cancelButton.img.get_width()//2 - 10
            self.pauseButton.y = self.buttonY + self.buttonHeight//2# + self.pauseButton.img.get_height()
            self.pauseButton.x += 3*self.pauseButton.img.get_width()//2 -10
            self.addTimeButton.y = self.buttonY + self.buttonHeight//2# + self.addTimeButton.img.get_height()
            self.addTimeButton.x += 3*self.addTimeButton.img.get_width()//2-10
            self.oldY = self.y

        self.cancelButton.selectAndConfirmLogic(cursorX,cursorY)
        self.pauseButton.selectAndConfirmLogic(cursorX,cursorY)
        self.addTimeButton.selectAndConfirmLogic(cursorX,cursorY)

        if self.on:
            self.remainingTime = self.totalTime - (time.time() - self.initTime) + self.additional
        if self.remainingTime <= 0:
            self.done = True
            self.remainingTime = 0
            self.on = False
            self.bgCol = lerp((100,255,100),(0,0,0),.4)
    
    def togglePause(self):
        if not self.on:
            self.pauseButton.changeImage(self.pausePath)
        else:
            self.pauseButton.changeImage(self.playPath)
        self.on = not self.on



    def timeToString(self):
        hoursLeft = int(self.remainingTime / 3600)
        minsLeft = int((self.remainingTime % 3600) / 60)
        secondsLeft = int(self.remainingTime % 60)
        hourZ = ""
        minZ = ""
        secZ = ""
        if hoursLeft < 10:
            hourZ = "0"
        if minsLeft < 10:
            minZ = "0"
        if secondsLeft < 10:
            secZ = "0"
        return hourZ+str(hoursLeft)+":"+minZ+str(minsLeft)+":"+secZ+str(secondsLeft)
        
    def addTime(self,num):
        self.additional += num*60

    def draw(self,screen,cursorX,cursorY):
        aa_round_rect(screen, (self.x,self.y,self.width,self.height), self.mainColor, 5, 3, self.bgCol)
        msg = self.titlefont.render(self.title, True, self.mainColor)
        screen.blit(msg,(self.x+self.width//2-msg.get_width()//2,self.y+10))
        num = self.timefont.render(self.timeToString(), True, self.mainColor)
        screen.blit(num,(self.x+self.width//2-num.get_width()//2,self.y+self.height//4))
        
        self.cancelButton.draw(screen,cursorX,cursorY)
        self.pauseButton.draw(screen,cursorX,cursorY)
        self.addTimeButton.draw(screen,cursorX,cursorY)
        

class Button:
    def __init__(self, x, y, width, height, text, font = 'Default Font', bgCol = 'Default BG Color', border = 3):
        if font == 'Default Font':
            self.font = pg.font.Font(os.path.abspath('Fonts/BalooThambi2-Regular.ttf'),30);
        else:
            self.font = font
        if bgCol == 'Default BG Color':
            self.baseColor = (10,10,10)
        else:
            self.baseColor = bgCol
        self.borderthickness = border

        self.mainColor = (255,255,255)
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.text = text
        self.selecting = False
        self.confirmed = False
        self.selectTimer = 0
        self.hovering = False

    def selectAndConfirmLogic(self,mouseX,mouseY):
        #mouse in box
        if (self.x - self.width/2 <= mouseX <= self.x + self.width/2) and (self.y - self.height/2 <= mouseY <= self.y + self.height/2):
            
            self.hovering = True
            if not self.confirmed:
                #confirmed
                if self.selectTimer >= 1:
                    self.selecting = False
                    self.confirmed = True
                    self.selectTimer = 0

                #still selecting
                if not self.selecting:
                    self.selecting = True

                #tick clock while mouse is in
                self.selectTimer += .1
            else:
                self.selecting = False
                self.selectTimer = 0
        #mouse moved
        else: #maybe needs to be confirmed?s
            self.hovering = False
            self.selecting = False
            self.selectTimer = 0


    def percentToAngle(self, percent):
        return mapTo(percent,0,1,0,320)

    def mouseSelectingDraw(self,screen,cursorX,cursorY):
            pg.gfxdraw.pie(screen, cursorX, cursorY, 35, 0, int(self.percentToAngle(self.selectTimer)), self.mainColor)

    def draw(self, screen,cursorX,cursorY):
        color = self.baseColor
        if self.selecting:
            color = (75,75,75)
        if self.confirmed:
            color = (100,100,100)

        msg = self.font.render(self.text, True, self.mainColor)
        if self.borderthickness != 0: 
            aa_round_rect(screen, (self.x-self.width/2,self.y-self.height/2,self.width,self.height), self.mainColor, 5, self.borderthickness, color)
        else:
            aa_round_rect(screen, (self.x-self.width/2,self.y-self.height/2,self.width,self.height), color, 5, self.borderthickness, color)
        screen.blit(msg,(self.x - msg.get_width()/2,self.y - msg.get_height()/2))
        
        if self.selecting:
            self.mouseSelectingDraw(screen,cursorX,cursorY)


class IconButton(Button):
    def __init__(self, x, y, width, height, text, font = 'Default Font', bgCol = 'Default BG Color', border = 3, imgPath = ''):
        #pass recipe's title in as the the button title
        super().__init__(x, y, width, height, text, font, bgCol, border)
        self.img = pg.image.load(imgPath)

    def changeImage(self,path):
        self.img = pg.image.load(path)

    def draw(self, screen,cursorX,cursorY):
        color = self.baseColor
        if self.selecting:
            color = lerp(color,(255,255,255),.4)

        if self.confirmed:
            color = lerp(color,(255,255,255),.8)

        aa_round_rect(screen, (self.x-self.width/2,self.y-self.height/2,self.width,self.height), self.mainColor, 5, self.borderthickness, color)
        screen.blit(self.img,(self.x - self.img.get_width()/2,self.y - self.img.get_height()/2))
        

        if self.selecting:
            self.mouseSelectingDraw(screen,cursorX,cursorY)

class RecipeButton(Button):
    def __init__(self, x, y, width, height, recipe):
        #pass recipe's title in as the the button title
        super().__init__(x, y, width, height, recipe['title'])
        self.tipfont = pg.font.Font(os.path.abspath('Fonts/BalooThambi2-Regular.ttf'),20);
        self.recipe = recipe
        self.complexity = self.getComplexity()
        self.activeTime = 0
        self.passiveTime = 0
        self.calculateTimes()
        self.totalTime = self.activeTime + self.passiveTime

    def calculateTimes(self):
        passiveTime = 0
        activeTime = 0
        for step in self.recipe['steps']:
            activeTime += step['active_time']
            passiveTime += step['passive_time']
        self.passiveTime = passiveTime
        self.activeTime = activeTime

    def getComplexity(self):
        ingredients = dict()
        units = dict()

        for step in self.recipe['steps']:
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
        return len(ingredients)

    def getIngredients(self):
        ingredients = dict()
        units = dict()

        for step in self.recipe['steps']:
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

    def draw(self,screen,cursorX,cursorY):
        super().draw(screen,cursorX,cursorY)
        if self.hovering:
            self.drawToolTip(screen)

    def drawToolTip(self,screen):
        msg = self.tipfont.render('Time: '+ str(self.totalTime)+" mins ("+str(self.activeTime)+" active, "+str(self.passiveTime)+" passive)" +  ' -- Total Ingredients: ' + str(self.complexity), True, (204,204,0))
        aa_round_rect(screen, (self.x-5,self.y+15,msg.get_width()+10,msg.get_height()),(100,100,100), 5, 1, self.baseColor)
        screen.blit(msg,(self.x,self.y+15))

def round_rect(surface, rect, color, rad=20, border=0, inside=(0,0,0,0)):
    # Draw a rect with rounded corners to surface.  Argument rad can be specified
    # to adjust curvature of edges (given in pixels).  An optional border
    # width can also be supplied; if not provided the rect will be filled.
    # Both the color and optional interior color (the inside argument) support
    # alpha.
    rect = pg.Rect(rect)
    zeroed_rect = rect.copy()
    zeroed_rect.topleft = 0,0
    image = pg.Surface(rect.size).convert_alpha()
    image.fill((0,0,0,0))
    _render_region(image, zeroed_rect, color, rad)
    if border:
        zeroed_rect.inflate_ip(-2*border, -2*border)
        _render_region(image, zeroed_rect, inside, rad)
    surface.blit(image, rect)


def _render_region(image, rect, color, rad):
    """Helper function for round_rect."""
    corners = rect.inflate(-2*rad, -2*rad)
    for attribute in ("topleft", "topright", "bottomleft", "bottomright"):
        pg.draw.circle(image, color, getattr(corners,attribute), rad)
    image.fill(color, rect.inflate(-2*rad,0))
    image.fill(color, rect.inflate(0,-2*rad))


def aa_round_rect(surface, rect, color, rad=20, border=0, inside=(0,0,0)):
    """
    Draw an antialiased rounded rect on the target surface.  Alpha is not
    supported in this implementation but other than that usage is identical to
    round_rect.
    """
    rect = pg.Rect(rect)
    _aa_render_region(surface, rect, color, rad)
    if border:
        rect.inflate_ip(-2*border, -2*border)
        _aa_render_region(surface, rect, inside, rad)


def _aa_render_region(image, rect, color, rad):
    """Helper function for aa_round_rect."""
    corners = rect.inflate(-2*rad-1, -2*rad-1)
    for attribute in ("topleft", "topright", "bottomleft", "bottomright"):
        x, y = getattr(corners, attribute)
        gfxdraw.aacircle(image, x, y, rad, color)
        gfxdraw.filled_circle(image, x, y, rad, color)
    image.fill(color, rect.inflate(-2*rad,0))
    image.fill(color, rect.inflate(0,-2*rad))