import wx

from ..errors import show_message


class AuthDialog(wx.Dialog):
    def __init__(self, parent, message, error=None, require_value=False):
        super().__init__(parent, title='Contraseña del puerto de control de Tor')
        self._require_value = require_value

        sizer = wx.BoxSizer(wx.VERTICAL)
        if error:
            sizer.Add(wx.StaticText(self, label=error), 0, wx.ALL, 10)
        text = wx.StaticText(self, label=message)
        text.Wrap(420)
        sizer.Add(text, 0, wx.LEFT | wx.RIGHT | wx.TOP, 10)

        sizer.Add(wx.StaticText(self, label='&Contraseña:'), 0, wx.LEFT | wx.RIGHT | wx.TOP, 10)
        self.password = wx.TextCtrl(self, style=wx.TE_PASSWORD)
        sizer.Add(self.password, 0, wx.EXPAND | wx.ALL, 10)

        self.remember = wx.CheckBox(self, label='&Recordar la contraseña (se guardará sin cifrar en el disco)')
        sizer.Add(self.remember, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        sizer.Add(self.CreateSeparatedButtonSizer(wx.OK | wx.CANCEL), 0, wx.EXPAND | wx.ALL, 10)
        self.SetSizerAndFit(sizer)
        self.CentreOnParent()
        self.password.SetFocus()
        self.Bind(wx.EVT_BUTTON, self._on_ok, id=wx.ID_OK)

    def _on_ok(self, event):
        if self._require_value and not self.password.GetValue():
            show_message(self, 'Escriba una contraseña.', 'Contraseña vacía', wx.ICON_WARNING)
            self.password.SetFocus()
            return
        event.Skip()

    def get_result(self):
        return self.password.GetValue(), self.remember.IsChecked()


def ask_password(parent, message, error=None, require_value=False):
    """Devuelve (contraseña, recordar) o None si se cancela."""
    with AuthDialog(parent, message, error, require_value) as dialog:
        if dialog.ShowModal() == wx.ID_OK:
            return dialog.get_result()
    return None
