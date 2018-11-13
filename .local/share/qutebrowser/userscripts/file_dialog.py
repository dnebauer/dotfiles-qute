#!/usr/bin/env python

from __future__ import print_function
import wx

app = wx.App()

frame = wx.Frame(None, -1, 'win.py')
frame.SetDimensions(0, 0, 200, 50)

# Create open file dialog
message = "Save as..."
default_dir = "/home/david/Downloads"
default_file = "BJI001.md"
glob = "Markdown files (*.md)|*.md"
with wx.FileDialog(frame, message, default_dir, default_file, glob,
                   wx.FD_SAVE) as fileDialog:

    if fileDialog.ShowModal() != wx.ID_CANCEL:
        save_path = fileDialog.GetPath()
        print('Save file as ' + save_path)
#   try:
#      with open(save_path, 'w') as file:
#           self.doSaveData(file)
#       except IOError:
#           wx.LogError("Cannot save current data in file '%s'." % save_path)
# idiom for writing file:
# with open(os.path.join(self.dirname, self.filename), 'w') as filehandle:
#    filehandle.write(contents)
