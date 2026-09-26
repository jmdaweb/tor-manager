"""Iconos de la aplicación dibujados en tiempo de ejecución."""

import wx

_CONNECTED = wx.Colour(125, 70, 152)
_DISCONNECTED = wx.Colour(128, 128, 128)


def make_bitmap(size, connected=True):
    bitmap = wx.Bitmap.FromRGBA(size, size, 0, 0, 0, 0)
    dc = wx.MemoryDC(bitmap)
    gc = wx.GraphicsContext.Create(dc)
    colour = _CONNECTED if connected else _DISCONNECTED
    centre = size / 2.0
    for ratio, width in ((0.46, max(1.5, size / 12.0)), (0.30, max(1.2, size / 14.0))):
        radius = size * ratio
        gc.SetPen(gc.CreatePen(wx.GraphicsPenInfo(colour).Width(width)))
        gc.SetBrush(wx.TRANSPARENT_BRUSH)
        gc.DrawEllipse(centre - radius, centre - radius, radius * 2, radius * 2)
    inner = size * 0.14
    gc.SetPen(wx.TRANSPARENT_PEN)
    gc.SetBrush(wx.Brush(colour))
    gc.DrawEllipse(centre - inner, centre - inner, inner * 2, inner * 2)
    del gc
    dc.SelectObject(wx.NullBitmap)
    return bitmap


def make_icon(size=32, connected=True):
    icon = wx.Icon()
    icon.CopyFromBitmap(make_bitmap(size, connected))
    return icon


def make_icon_bundle(connected=True):
    bundle = wx.IconBundle()
    for size in (16, 24, 32, 48):
        bundle.AddIcon(make_icon(size, connected))
    return bundle
