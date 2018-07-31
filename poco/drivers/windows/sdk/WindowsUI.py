# coding=utf-8

from poco.sdk.std.rpc.controller import StdRpcEndpointController
from poco.sdk.std.rpc.reactor import StdRpcReactor
from poco.utils.net.transport.tcp import TcpSocket

from WindowsUIDumper import WindowsUIDumper
from WindowsUINode import WindowsUINode
from poco.sdk.exceptions import UnableToSetAttributeException
from poco.utils.six import text_type
from uiautomation import uiautomation as UIAuto
import time
import json
import base64
import zlib
import win32api
import win32con
import win32gui
import re

DEFAULT_PORT = 15004
DEFAULT_ADDR = ('0.0.0.0', DEFAULT_PORT)


class PocoSDKWindows(object):

    def __init__(self, addr=DEFAULT_ADDR):
        self.reactor = StdRpcReactor()
        self.reactor.register('Dump', self.Dump)
        self.reactor.register('SetText', self.SetText)
        self.reactor.register('GetSDKVersion', self.GetSDKVersion)
        self.reactor.register('GetDebugProfilingData', self.GetDebugProfilingData)
        self.reactor.register('GetScreenSize', self.GetScreenSize)
        self.reactor.register('Screenshot', self.Screenshot)
        self.reactor.register('Click', self.Click)
        self.reactor.register('Swipe', self.Swipe)
        self.reactor.register('LongClick', self.LongClick)
        self.reactor.register('KeyEvent', self.KeyEvent)
        self.reactor.register('SetForeground', self.SetForeground)
        self.reactor.register('ConnectWindow', self.ConnectWindow)

        transport = TcpSocket()
        transport.bind(addr)
        self.rpc = StdRpcEndpointController(transport, self.reactor)

        self.running = False
        UIAuto.OPERATION_WAIT_TIME = 0.1  # make operation faster
        self.root = None

    def Dump(self, _):
        res = WindowsUIDumper(self.root).dumpHierarchy()
        return res

    def SetText(self, id, val2):
        control = UIAuto.ControlFromHandle(id)
        if not control or not isinstance(val2, basestring):
            raise UnableToSetAttributeException("text", control)
        else:
            control.SetValue(val2)

    def GetSDKVersion(self):
        return '0.0.1'

    def GetDebugProfilingData(self):
        return {}

    def GetScreenSize(self):
        Width = self.root.BoundingRectangle[2] - self.root.BoundingRectangle[0]
        Height = self.root.BoundingRectangle[3] - self.root.BoundingRectangle[1]
        return [Width, Height]

    def Screenshot(self, width):
        # 如果采用压缩，PocoHierarchyViewer获取不到背景（当前Viewer版本还没支持）
        self.root.ToBitmap().ToFile('Screenshot.bmp')
        f = open(r'Screenshot.bmp', 'rb')
        deflated = zlib.compress(f.read())
        ls_f = base64.b64encode(deflated)
        f.close()
        return [ls_f, "bmp.deflate"]

        # self.root.ToBitmap().ToFile('Screenshot.bmp')
        # f = open(r'Screenshot.bmp', 'rb')
        # ls_f = base64.b64encode(f.read())
        # f.close()
        # return [ls_f, "bmp"]

    def Click(self, x, y):
        self.root.Click(x, y)
        return True

    def Swipe(self, x1, y1, x2, y2, duration):
        Left = self.root.BoundingRectangle[0]
        Top = self.root.BoundingRectangle[1]
        Width = self.root.BoundingRectangle[2] - self.root.BoundingRectangle[0]
        Height = self.root.BoundingRectangle[3] - self.root.BoundingRectangle[1]
        x1 = Left + Width * x1
        y1 = Top + Height * y1
        x2 = Left + Width * x2
        y2 = Top + Height * y2
        UIAuto.MAX_MOVE_SECOND = duration * 10
        UIAuto.DragDrop(int(x1), int(y1), int(x2), int(y2))
        return True

    def LongClick(self, x, y, duration):
        Left = self.root.BoundingRectangle[0]
        Top = self.root.BoundingRectangle[1]
        Width = self.root.BoundingRectangle[2] - self.root.BoundingRectangle[0]
        Height = self.root.BoundingRectangle[3] - self.root.BoundingRectangle[1]
        x = Left + Width * x
        y = Top + Height * y
        UIAuto.MAX_MOVE_SECOND = duration * 10
        UIAuto.DragDrop(int(x), int(y), int(x), int(y))
        return True

    def KeyEvent(self, keycode):
        UIAuto.SendKeys(keycode)
        return True

    def SetForeground(self):
        win32gui.ShowWindow(self.root.Handle, win32con.SW_SHOWNORMAL)
        UIAuto.Win32API.SetForegroundWindow(self.root.Handle)
        return True

    def ConnectWindowsByTitle(self, title):
        hn = set()
        hWndList = []

        def foo(hwnd, mouse):
            if win32gui.IsWindow(hwnd):
                hWndList.append(hwnd)
        win32gui.EnumWindows(foo, 0)
        for handle in hWndList:
            title_temp = win32gui.GetWindowText(handle)
            if title == title_temp.decode("gbk"):
                hn.add(handle)
        if len(hn) == 0:
            return -1
        return hn

    def ConnectWindowsByTitleRe(self, title_re):
        hn = set()
        hWndList = []

        def foo(hwnd, mouse):
            if win32gui.IsWindow(hwnd):
                hWndList.append(hwnd)
        win32gui.EnumWindows(foo, 0)
        for handle in hWndList:
            title = win32gui.GetWindowText(handle)
            if re.match(title_re, title.decode("gbk")):
                hn.add(handle)
        if len(hn) == 0:
            return -1
        return hn

    def ConnectWindowsByHandle(self, handle):
        hn = set()
        hWndList = []

        def foo(hwnd, mouse):
            if win32gui.IsWindow(hwnd):
                hWndList.append(hwnd)
        win32gui.EnumWindows(foo, 0)
        for handle_temp in hWndList:
            if int(handle_temp) == int(handle):
                hn.add(handle)
                break
        if len(hn) == 0:
            return -1
        return hn

    def ConnectWindow(self, selector, foreground=False):
        if foreground:
            time.sleep(1)
            self.root = UIAuto.GetForegroundControl()
            return True

        handleSetList = []
        if 'title' in selector:
            res = self.ConnectWindowsByTitle(selector['title'])
            if res != -1:
                handleSetList.append(res)
        if 'handle' in selector:
            res = self.ConnectWindowsByHandle(selector['handle'])
            if res != -1:
                handleSetList.append(res)
        if "title_re" in selector:
            res = self.ConnectWindowsByTitleRe(selector['title_re'])
            if res != -1:
                handleSetList.append(res)

        # If there are multiple matches, return a random one
        if len(handleSetList) == 1:
            hn = handleSetList[0].pop()
            if hn:
                self.root = UIAuto.ControlFromHandle(hn)
                return True
            else:
                return False

        last = handleSetList[0]
        for hn in handleSetList:
            print hn
            last = hn & last
            
        if len(last) == 0:
            return False
        else:
            # If there are multiple matches, return a random one
            hn = last.pop()
            if hn:
                self.root = UIAuto.ControlFromHandle(hn)
                return True
            else:
                return False

    def run(self, use_foregrond_window=False):
        if self.running is False:
            self.running = True
            if use_foregrond_window:
                self.ConnectWindow(set(), True)

            # print "Current Window :", self.root.Name
            self.rpc.serve_forever()


if __name__ == '__main__':
    pocosdk = PocoSDKWindows()
    pocosdk.run(True)
