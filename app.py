# APP IMPORTS
from tree import Tree
from transducer import QTreeTrans
import re

# KIVY IMPORTS
from kivy.config import Config
Config.set('input', 'mouse', 'mouse,multitouch_on_demand')

import kivy

from kivy.app import App
from kivy.properties import NumericProperty, ObjectProperty, BooleanProperty
from kivy.core.text import Label as CoreLabel
from kivy.uix.label import Label
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.textinput import TextInput
from kivy.uix.widget import Widget
from kivy.core.window import Window
from kivy.graphics import Color, Ellipse, Rectangle, Line
from kivy.clock import Clock

# CONSTANTS

DEFAULT_TRANSDUCER = QTreeTrans
SPROUT_DIST = 20.
POS_ABS_ROOT = (0, 80)
EXPONENT = 1.1

# MAIN CODE

# Construction of the default tree
main = Tree()
main.sprout(0)
main.sprout(1)
main.sprout(2)
main.sprout(4)
main.sprout(6)


# HELPER FUNCTIONS
def dist(p1, p2):
	return ((p1[0] - p2[0])**2 + (p1[1] - p2[1])**2)**0.5


# Left widget: displays tree in Canvas

class TreeDisplay(Widget):
	# Fires event when structural changes were made to the tree
	treeChange = BooleanProperty(False)
	# Fires event when changes to the display need to be made
	displayChange = BooleanProperty(False)


	def __init__(self, **kwargs):
		super(TreeDisplay, self).__init__(**kwargs)

		# Position of canvas center in absolute coordinates
		self.absCenter = 0, 0 
		# Zoom level
		self.scale = 0.5

		# Compute position of nodes in tree in absolute coordinates if root is at POS_ABS_ROOT in absolute coordinates
		main.construct(POS_ABS_ROOT)

		# 1s after start, display Tree (why is this needed for proper drawing?)
		Clock.schedule_once(lambda dt: self.drawTree(main), 60./60.)

	# Convenience aliases
	@property
	def absX(self):
		return self.absCenter[0]

	@property
	def absY(self):
		return self.absCenter[1]
	
	# Transform point and vector from absolute coordinates to canvas coordinates in vice-versa
	def toLocal(self, x, y):
		return ((1. / self.scale) * (x - self.absX) + self.center[0],
				 (1. / self.scale) * (y - self.absY) + self.center[1])

	# vectors only
	def toLocalS(self, x, y):
		return ((1. / self.scale) * x,
				 (1. / self.scale) * y)

	def toAbs(self, x, y):
		return ((self.scale) * (x - self.center[0]) + self.absX,
				 (self.scale) * (y - self.center[1]) + self.absY)

	# vectors only
	def toAbsS(self, x, y):
		return ((self.scale) * x,
				 (self.scale) * y)

	# Redraws tree
	def drawTree(self, tree): 
		self.canvas.clear()

		defaults = {"radiusPts": 10., "thickLines": 2, "colorDots" : (1,0,0), "fontSize": 10, "colorText": (0, 1, 0)}

		# Convert node positions in canvas coordinates
		lPos = [self.toLocal(*p) for p in tree.positions]


		with self.canvas:
			# Display lines first
			for i in range(tree.n):
				if tree.children[i]:
					for c in tree.children[i]:
						Line(points = (lPos[i][0], lPos[i][1], lPos[c][0], lPos[c][1]),
													width = defaults["thickLines"])
		
			Color(*defaults["colorDots"])
			
			# Display nodes	
			r = defaults["radiusPts"]
			for p in lPos:
				Ellipse(pos = (p[0] - r/2., p[1] - r/2.), size = (r, r))

			Color(*defaults["colorText"])

		# Display labels
		for i in range(tree.n):
			l = CoreLabel(text = tree.labels[i], font_size = defaults["fontSize"])
			l.refresh()
			self.canvas.add(Rectangle(size = l.texture.size, pos = lPos[i], texture = l.texture))



	def on_touch_down(self, touch):
		if self.collide_point(*touch.pos):
			# Scrolling zooms in
			if touch.is_mouse_scrolling:
				self.zoom(1. if touch.button == "scrollup" else -1.)
				self.displayChange = not self.displayChange
				return True
			# Middle button to grab
			# Saves initial position of touch and initial center of canvas in absolute coordinates
			elif "button" in touch.profile and touch.button == "middle":
				touch.ud["posInit"] = touch.pos
				touch.ud["initPos"] = self.absX, self.absY
				return True
		
		# If a left or right click, we check whether the event occurs in the vicinity of a node
		# The notion of vicinity is scaled for zooming
		for i, p in enumerate(main.positions):
			if dist(self.toLocal(*p), touch.pos) < SPROUT_DIST / self.scale:
				if "button" in touch.profile and touch.button == "left":
					main.sprout(i)
					self.treeChange = not self.treeChange
					return True
				elif "button" in touch.profile and touch.button == "right":
					main.delete(i)
					self.treeChange = not self.treeChange
					return True

	# For middle mouse grab
	def on_touch_move(self, touch):
		if "button" in touch.profile and touch.button == "middle":
			# Compute the displacement vector between original position of touch and current position of touch in absolute coordinates
			displacement = self.toAbsS(touch.ud["posInit"][0] - touch.pos[0], touch.ud["posInit"][1] - touch.pos[1])
			# Add displacement vector to initial position of canvas center
			# So that the point where the middle mouse click was initiated is exactly where the mouse currently is
			self.absCenter = touch.ud["initPos"][0] + displacement[0], touch.ud["initPos"][1] + displacement[1]
			# Refresh display
			self.displayChange = not self.displayChange
	
	# Event handler when structural modifications have been made to the tree
	def on_treeChange(self, instance, pos):
		main.construct(POS_ABS_ROOT)
		self.displayChange = not self.displayChange

	# When Display needs refreshing
	def on_displayChange(self, instance, pos):
		self.drawTree(main)

	def zoom(self, value):
		self.scale *= EXPONENT**(value)


# Right widget : displays the tree in string format and allows input of labels
class TreeInput(TextInput):

	def __init__(self, **kwargs):
		super(TreeInput, self).__init__(**kwargs)
		# Refresh string display
		self.updateTree()

		# Enter does not defocus widget
		# This is not working but may in other versions of kivy
		self.text_validate_unfocus = False


	def updateTree(self):
		# Get RegExp associated with tree
		# This is an expression that matches any string that represents a tree identical to main, except possibly for the labels
		self.pat = DEFAULT_TRANSDUCER.regExp(main)
		# This is the actual string representation of the tree
		self.text = DEFAULT_TRANSDUCER.toStr(main) 

	# Disallow modification of the structure of the tree in the text input
	def insert_text(self, substring, from_undo = False):
		# What comes before and after the inserted text
		before = self.text[:self.cursor_index()]
		after = self.text[self.cursor_index():]

		# If change results in modifying tree structure, cancel
		s = "" if self.pat.match(before + substring + after) is None else substring
		return super(TreeInput, self).insert_text(s, from_undo=from_undo)

	# When text changes, modify the labels accordingly
	# Structure is not allowed to change
	def on_text(self, instance, text):
		# use reg exp to recover labels
		m = self.pat.match(self.text)


		if m is not None:
			groups = m.groups()
			# Labels are obtained from the regexp in the linear order in which they are displayed
			# This may not be the order in which they are stored
			# We compute a table that matches linear order position to stored position
			inds = DEFAULT_TRANSDUCER.indicesOrder(main)

			# Modify the labels
			for i, g in enumerate(groups):
				main.labels[inds[i]] = g



class MainWindow(BoxLayout):
	pass

class TreeApp(App):

    def build(self):
        return MainWindow()


if __name__ == '__main__':
    TreeApp().run()