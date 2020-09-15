#!/usr/bin/env python

import wx
import subprocess
import shlex
from enum import Enum
import json
import math
from math import pi
from math import atan2
import signal
import os
from pathlib import Path


TWO_PI = pi * 2


def parse_command(command):
    print('parsing: ', command)
    command_dict = {
        "href": "google-chrome-stable",
    }
    segments = command.split()
    if len(segments) < 2:
        return command
    if segments[0] in command_dict:
        return f"{command_dict[segments[0]]} {' '.join(segments[1:])}"
    else:
        return command


def load_data():
    with open('data/template.json') as f:
        data = json.load(f)
    return data


def overPie(pie):
    return pie.over


def dist(frm, to):
    fromX, fromY = frm
    toX, toY = to
    return math.sqrt((fromX-toX)**2 + (fromY-toY)**2)


def deg(rad):
    degreeResult = rad * 180 / pi
    return degreeResult


try:
    import wx.lib.wxcairo as wxcairo
    import cairo
    haveCairo = True
except ImportError:
    haveCairo = False


class Actions(Enum):
    NONE = 0
    MENU = 1
    EXECUTION = 2


class RadAction():
    def __init__(self, menu=None, execution=None):
        self.type = Actions.NONE
        self.menu = menu
        self.execution = execution
        self.LoadType(menu, execution)

    def LoadType(self, menu, execution):
        if menu == None:
            self.type = Actions.EXECUTION
        else:
            self.type = Actions.MENU


class Pie():
    def __init__(self, startAngle, endAngle, brush, center, length, pieData):
        self.over = False
        self.over_offset = math.radians(15)
        self.startAngle = startAngle
        self.endAngle = endAngle
        self.center = center
        self.length = length
        if 'color' in pieData:
            color = pieData['color']
            if color[0] != '#':
                color = f"#{color}"
            self.brush = wx.Brush(color)
        else:
            self.brush = brush
        self.pieData = pieData
        self.w = 800
        self.h = 800

    def Activate(self):
        if 'menu' in self.pieData:
            return RadAction(menu=RadMenu(self.pieData, self.w, self.h))
        else:
            return RadAction(execution=self.Execution())
        pass

    def Execution(self):
        if 'action' in self.pieData:
            return self.pieData['action']
        return None

    def DrawText(self, dc):
        textAngle = self.startAngle + ((self.endAngle - self.startAngle) * 0.5)
        x_off = math.cos(textAngle) * self.length * 0.6
        y_off = math.sin(textAngle) * self.length * 0.6
        (x, y) = self.center
        dc.SetFont(wx.Font(20, wx.DEFAULT, wx.NORMAL, wx.NORMAL))
        overText = "o"
        if self.over:
            overText = "x"

        center_x, center_y = int(x + x_off), int(y + (y_off*-1))
        rect_offset = 50
        rect = wx.Rect(center_x - rect_offset, center_y -
                       rect_offset, rect_offset*2, rect_offset)

        dc.DrawLabel(self.pieData['name'],
                     rect, wx.ALIGN_CENTER | wx.ALIGN_TOP)

    def StartAngle(self):
        if self.over:
            return self.startAngle - self.over_offset
        return self.startAngle

    def EndAngle(self):
        if self.over:
            return self.endAngle + self.over_offset
        return self.endAngle

    def Draw(self, dc):
        dc.SetBrush(self.brush)
        start, end = self.Calc()
        dc.SetPen(wx.Pen('#FFFFFF', 0))
        dc.DrawEllipticArc(0, 0, 800, 800, math.degrees(
            start), math.degrees(end))
        dc.SetPen(wx.Pen('#FFFFFF', 2))
        self.DrawText(dc)
        if self.over:
            cx, cy = self.center
            end_x = cx + math.cos(start) * (self.length)
            end_y = cy - math.sin(start) * (self.length)
            dc.DrawLine(cx, cy, int(end_x), int(end_y))

            end_x = cx + math.cos(end) * (self.length)
            end_y = cy - math.sin(end) * (self.length)
            dc.DrawLine(cx, cy, int(end_x), int(end_y))

    def Calc(self):
        return (self.StartAngle(), self.EndAngle())

    def Recalculate(self, relativePos):
        over = self.IsOver(relativePos)
        if self.over == over:
            return False
        else:
            self.over = over
            return True

    def IsOver(self, relativePos):
        x, y = relativePos

        y *= -1

        hoverStart = self.startAngle
        hoverEnd = self.endAngle

        r_angle = atan2(y, x)
        if r_angle < 0:
            r_angle += TWO_PI

        if r_angle > hoverStart and r_angle < hoverEnd:
            return True
        return False


class RadMenu():
    def __init__(self, data, w, h):
        self.w = w
        self.h = h
        self.data = data
        self.slices = 6
        self.center = (int(w/2), int(h/2))
        self.pies = self.SetupPies()

    def SetupPies(self):
        brushes = [
            wx.Brush('#90BEDE'),
            wx.Brush('#8fe388'),
            wx.Brush('#f15152'),
            wx.Brush('#ffd275'),
        ]
        pies = []
        self.slices = len(self.data['menu'])
        step = TWO_PI / self.slices
        i = 0
        for pieData in self.data['menu']:
            brush = brushes[i % len(brushes)]
            pies.append(Pie(i * step, (i+1) * step,
                            brush, self.center, self.w/2, pieData))
            i += 1
        return pies

    def OnLeftDown(self, evt):
        over = [pie for pie in self.pies if pie.over]
        if len(over) == 1:
            return over[0].Activate()

    def RedrawPies(self, dc):
        # dc.SetBackground(wx.WHITE_BRUSH)
        # dc.Clear()
        [pie.Draw(dc)
         for pie in sorted(self.pies, key=lambda p: p.over)]

    def OnMouseMove(self, dc, relMousePos):
        needsRedraw = any([pie.Recalculate(relMousePos)
                           for pie in self.pies])
        if needsRedraw:
            self.RedrawPies(dc)


TIMER_ID = 213


class Roundy(wx.Frame):
    def __init__(self, parent, log):
        self.log = log
        wx.Frame.__init__(self, parent, -1, "Shaped Window",
                          style=wx.FRAME_SHAPED
                          | wx.SIMPLE_BORDER
                          | wx.FRAME_NO_TASKBAR
                          | wx.STAY_ON_TOP
                          | wx.TRANSPARENT_WINDOW
                          )

        self.hasShape = False
        self.delta = (0, 0)
        self.w = 800
        self.h = 800
        self.bmp = self.GetRoundBitmap()

        self.Bind(wx.EVT_LEFT_DCLICK, self.OnDoubleClick)
        self.Bind(wx.EVT_LEFT_DOWN,   self.OnLeftDown)
        self.Bind(wx.EVT_LEFT_UP,     self.OnLeftUp)
        self.Bind(wx.EVT_MOTION,      self.OnMouseMove)
        self.Bind(wx.EVT_RIGHT_UP,    self.OnRightUp)
        self.Bind(wx.EVT_PAINT,       self.OnPaint)
        self.Bind(wx.EVT_TIMER,        self.OnTimer)
        self.timer = wx.Timer(self, TIMER_ID)
        self.timer.Start(100)

        self.menus = []
        self.SetupMenu()

        # imagePath = "images/roundy.bmp"
        # image = wx.Bitmap(imagePath, wx.BITMAP_TYPE_BMP)
        # self.bmp = Vippi.GetBitmap()

        # self.svg = wx.SVGImage.CreateFromFile("images/round.svg")

        w, h = self.bmp.GetWidth(), self.bmp.GetHeight()
        self.SetClientSize((w, h))

        if wx.Platform != "__WXMAC__":
            # wxMac clips the tooltip to the window shape, YUCK!!!
            self.SetToolTip("Right-click to close the window\n"
                            "Double-click the image to set/unset the window shape")

        if wx.Platform == "__WXGTK__":
            # wxGTK requires that the window be created before you can
            # set its shape, so delay the call to SetWindowShape until
            # this event.
            self.Bind(wx.EVT_WINDOW_CREATE, self.SetWindowShape)
        else:
            # On wxMSW and wxMac the window has already been created, so go for it.
            self.SetWindowShape()

        dc = wx.ClientDC(self)
        dc.DrawBitmap(self.bmp, 0, 0, True)

    def RadialNotification(self, notification):
        print(notification)

    def OnTimer(self, evt):
        pass

    def SetupMenu(self):
        self.data = load_data()
        self.PushMenu(RadMenu(self.data, self.w, self.h))

    def GetRoundBitmap(self):
        w = self.w
        h = self.h
        maskColor = wx.Colour(0, 0, 0)
        shownColor = wx.Colour(5, 5, 5)
        b = wx.Bitmap(w, h)
        dc = wx.MemoryDC()
        dc.SelectObject(b)
        dc.SetBrush(wx.Brush(maskColor))
        dc.DrawRectangle(0, 0, w, h)
        dc.SetBrush(wx.Brush(shownColor))
        dc.DrawCircle(int(w/2), int(h/2), int(w/2))
        dc.SelectObject(wx.NullBitmap)
        b.SetMaskColour(maskColor)
        return b

    def GetRoundShape(w, h, r):
        return wx.RegionFromBitmap(self.GetRoundBitmap(w, h, r))

    def SetWindowShape(self, *evt):
        # Use the bitmap's mask to determine the region
        # col = wx.Colour(0, 0, 0)
        r = wx.Region(self.bmp)
        self.hasShape = self.SetShape(r)

    def OnRightUp(self, evt):
        if len(self.menus) > 1:
            self.PopMenu()
        else:
            self.Background()

    def OnDoubleClick(self, evt):
        if self.hasShape:
            self.SetShape(wx.Region())
            self.hasShape = False
        else:
            self.SetWindowShape()

    def OnPaint(self, evt):
        if self.IsDoubleBuffered():
            dc = wx.PaintDC(self)
        else:
            dc = wx.BufferedPaintDC(self)

        gc = wx.GCDC(dc)

        self.menu.RedrawPies(gc)

    def OnExit(self, evt):
        self.Close()

    def PushMenu(self, menu):
        self.menus.append(menu)
        self.menu = self.menus[-1]

    def ResetMenu(self):
        self.menus = [self.menus[0]]
        self.menu = self.menus[0]

    def PopMenu(self):
        self.menus.pop()
        self.menu = self.menus[-1]

    def HandleAction(self, action):
        if action.type == Actions.MENU:
            self.PushMenu(action.menu)
        else:
            self.Execute(action.execution)

    def Execute(self, command):
        command = parse_command(command)
        print(f"running: {command}")
        args = shlex.split(command)
        print(f"args: {args}")
        pid = subprocess.Popen(args).pid
        if self.HasCapture():
            self.ReleaseMouse()
        self.Background()

    def Background(self):
        self.ResetMenu()
        self.Hide()

    def OnLeftDown(self, evt):
        self.CaptureMouse()
        action = self.menu.OnLeftDown(evt)
        self.HandleAction(action)

        # used to move window
        # x, y = self.ClientToScreen(evt.GetPosition())
        # originx, originy = self.GetPosition()
        # dx = x - originx
        # dy = y - originy
        # self.delta = ((dx, dy))

    def OnLeftUp(self, evt):
        if self.HasCapture():
            self.ReleaseMouse()

    def HalfW(self):
        return self.w / 2

    def HalfH(self):
        return self.h / 2

    def OnMouseMove(self, evt):
        pos = evt.GetPosition()
        relMousePos = (pos.x - self.HalfW(), pos.y - self.HalfH())
        dc = wx.ClientDC(self)
        gc = wx.GCDC(dc)
        self.menu.OnMouseMove(gc, relMousePos)
        # x, y = self.ClientToScreen(evt.GetPosition())
        # if evt.Dragging() and evt.LeftIsDown():
        #     fp = (x - self.delta[0], y - self.delta[1])
        #     self.Move(fp)


app = wx.App()


pid_no = str(os.getpid())
with open(f"{Path.home()}/.roundy.pid", 'w') as pid_file:
    pid_file.write(pid_no)

print(pid_no)


frm = Roundy(None, None)
frm.Show()


def signal_handler(sig, frame):
    frm.Show()


signal.signal(signal.SIGUSR1, signal_handler)
app.MainLoop()
