Attribute VB_Name = "Module1"
Option Explicit

Public PortNumber
Public date2 As String
Public Temp As String

Private Declare Function GetSystemMenu Lib "user32" _
    (ByVal hwnd As Long, _
     ByVal bRevert As Long) As Long

Private Declare Function RemoveMenu Lib "user32" _
    (ByVal hMenu As Long, _
     ByVal nPosition As Long, _
     ByVal wFlags As Long) As Long
     
Private Const MF_BYPOSITION = &H400&

Public Function DisableCloseButton(frm As Form) As Boolean

'PURPOSE: Removes X button from a form
'EXAMPLE: DisableCloseButton Me
'RETURNS: True if successful, false otherwise
'NOTES:   Also removes Exit Item from
'         Control Box Menu

    Dim lAns1 As Long, lAns2 As Long
    Dim lHndSysMenu As Long
         
    lHndSysMenu = GetSystemMenu(frm.hwnd, 0)
    
    'remove close button
    lAns1 = RemoveMenu(lHndSysMenu, 6, MF_BYPOSITION)

End Function
