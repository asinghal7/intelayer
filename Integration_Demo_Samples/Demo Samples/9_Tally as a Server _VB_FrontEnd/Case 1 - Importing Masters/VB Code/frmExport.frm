VERSION 5.00
Object = "{F9043C88-F6F2-101A-A3C9-08002B2F49FB}#1.2#0"; "COMDLG32.OCX"
Object = "{831FDD16-0C5C-11D2-A9FC-0000F8754DA1}#2.0#0"; "MSCOMCTL.OCX"
Begin VB.Form frmExport 
   BorderStyle     =   1  'Fixed Single
   Caption         =   "Data Transfer to Tally"
   ClientHeight    =   3015
   ClientLeft      =   45
   ClientTop       =   330
   ClientWidth     =   7350
   BeginProperty Font 
      Name            =   "MS Sans Serif"
      Size            =   8.25
      Charset         =   0
      Weight          =   700
      Underline       =   0   'False
      Italic          =   0   'False
      Strikethrough   =   0   'False
   EndProperty
   LinkTopic       =   "Form1"
   MaxButton       =   0   'False
   ScaleHeight     =   3015
   ScaleWidth      =   7350
   StartUpPosition =   3  'Windows Default
   Begin MSComctlLib.StatusBar sbExport 
      Align           =   2  'Align Bottom
      Height          =   375
      Left            =   0
      TabIndex        =   11
      Top             =   2640
      Width           =   7350
      _ExtentX        =   12965
      _ExtentY        =   661
      Style           =   1
      _Version        =   393216
      BeginProperty Panels {8E3867A5-8586-11D1-B16A-00C0F0283628} 
         NumPanels       =   1
         BeginProperty Panel1 {8E3867AB-8586-11D1-B16A-00C0F0283628} 
         EndProperty
      EndProperty
   End
   Begin VB.ComboBox cboImportType 
      Height          =   315
      Left            =   2400
      Style           =   2  'Dropdown List
      TabIndex        =   9
      Top             =   240
      Width           =   1935
   End
   Begin VB.TextBox txtPortNo 
      BeginProperty Font 
         Name            =   "MS Sans Serif"
         Size            =   8.25
         Charset         =   0
         Weight          =   400
         Underline       =   0   'False
         Italic          =   0   'False
         Strikethrough   =   0   'False
      EndProperty
      Height          =   350
      Left            =   2400
      MaxLength       =   5
      TabIndex        =   3
      Top             =   1680
      Width           =   1215
   End
   Begin VB.TextBox txtSystemName 
      BeginProperty Font 
         Name            =   "MS Sans Serif"
         Size            =   8.25
         Charset         =   0
         Weight          =   400
         Underline       =   0   'False
         Italic          =   0   'False
         Strikethrough   =   0   'False
      EndProperty
      Height          =   350
      Left            =   2400
      MaxLength       =   100
      TabIndex        =   2
      Top             =   1200
      Width           =   4335
   End
   Begin VB.CommandButton cmdExit 
      Cancel          =   -1  'True
      Caption         =   "E&xit"
      Height          =   375
      Left            =   4320
      TabIndex        =   5
      Top             =   2160
      Width           =   1215
   End
   Begin VB.CommandButton cmdExport 
      Caption         =   "E&xport to Tally"
      Height          =   375
      Left            =   2400
      TabIndex        =   4
      Top             =   2160
      Width           =   1455
   End
   Begin VB.CommandButton cmdFileOpen 
      Caption         =   "..."
      Height          =   375
      Left            =   6840
      TabIndex        =   1
      Top             =   720
      Width           =   375
   End
   Begin VB.TextBox txtFileName 
      BeginProperty Font 
         Name            =   "MS Sans Serif"
         Size            =   8.25
         Charset         =   0
         Weight          =   400
         Underline       =   0   'False
         Italic          =   0   'False
         Strikethrough   =   0   'False
      EndProperty
      Height          =   350
      Left            =   2400
      TabIndex        =   0
      Top             =   720
      Width           =   4335
   End
   Begin MSComDlg.CommonDialog cdlg 
      Left            =   120
      Top             =   2040
      _ExtentX        =   847
      _ExtentY        =   847
      _Version        =   393216
   End
   Begin VB.Label Label4 
      AutoSize        =   -1  'True
      Caption         =   "Type"
      Height          =   195
      Left            =   120
      TabIndex        =   10
      Top             =   300
      Width           =   435
   End
   Begin VB.Label Label3 
      AutoSize        =   -1  'True
      Caption         =   "Port No."
      Height          =   195
      Left            =   120
      TabIndex        =   8
      Top             =   1755
      Width           =   720
   End
   Begin VB.Label Label2 
      AutoSize        =   -1  'True
      Caption         =   "System Name/IP Address"
      Height          =   195
      Left            =   120
      TabIndex        =   7
      Top             =   1275
      Width           =   2160
   End
   Begin VB.Label Label1 
      AutoSize        =   -1  'True
      Caption         =   "File Name"
      Height          =   195
      Left            =   120
      TabIndex        =   6
      Top             =   795
      Width           =   855
   End
End
Attribute VB_Name = "frmExport"
Attribute VB_GlobalNameSpace = False
Attribute VB_Creatable = False
Attribute VB_PredeclaredId = True
Attribute VB_Exposed = False
Option Explicit
Dim xlApp As Excel.Application
Dim xlWb As Excel.Workbook
Dim xlWS As Excel.Worksheet


Private Sub cmdExit_Click()
Unload Me
End
End Sub

Private Sub cmdExport_Click()
On Error GoTo ERRIMPORT

Dim objXml As MSXML2.ServerXMLHTTP
Dim strXmldata As String
Dim intI As Integer
Dim lngF As Long
Dim lngRows As Long
Dim lngErrCnt As Long

sbExport.SimpleText = vbNullString
If Trim$(txtFileName.Text) = vbNullString Then
    MsgBox "Filename cannot be blank", , "Tally"
    txtFileName.SetFocus
    Exit Sub
Else
    If Dir(Trim$(txtFileName.Text)) = vbNullString Then
        MsgBox "Invalid Filename", , "Tally"
        txtFileName.Text = vbNullString
        txtFileName.SetFocus
        Exit Sub
    End If
End If

If Trim$(txtSystemName.Text) = vbNullString Then
    MsgBox "System Name/IP Address cannot be blank", , "Tally"
    txtSystemName.SetFocus
    Exit Sub
End If

If Trim$(txtPortNo.Text) = vbNullString Then
    MsgBox "Port No. cannot be blank", , "Tally"
    txtPortNo.SetFocus
    Exit Sub
End If


Set xlApp = New Excel.Application
Set xlWb = xlApp.Workbooks.open(txtFileName.Text)
Dim blnExist As Boolean

Select Case UCase(cboImportType.Text)
Case "LEDGERS"
    For Each xlWS In xlWb.Worksheets
        If xlWS.Name = "Ledgers" Then
            blnExist = True
            Exit For
        End If
    Next xlWS
    If blnExist = False Then
        MsgBox "Ledgers sheet doesn't exist"
        Exit Sub
    End If
Case "STOCK ITEMS"
    For Each xlWS In xlWb.Worksheets
        If xlWS.Name = "StockItems" Then
            blnExist = True
            Exit For
        End If
    Next xlWS
    If blnExist = False Then
        MsgBox "StockItems sheet doesn't exist"
        Exit Sub
    End If
Case Else
    Exit Sub
End Select

lngErrCnt = 0
lngRows = 25000
On Error Resume Next
lngRows = xlWS.Cells.End(xlDown).Row
On Error GoTo ERRIMPORT

lngF = FreeFile
Open App.Path & "\Tally.imp" For Append As lngF
Print #lngF, "**********************************************************************"
Print #lngF, " Exporting Data from " & " Filename: " & txtFileName.Text & "to Tally: " & "http://" & Trim$(txtSystemName.Text) & ":" & Trim$(txtPortNo.Text)
Print #lngF, " Start Time: " & Format(Now, "DD-MMM-YYYY HH:MM:SS")
Print #lngF, "**********************************************************************"

Set objXml = New MSXML2.ServerXMLHTTP

For intI = 2 To lngRows
    Screen.MousePointer = vbHourglass
    strXmldata = vbNullString
    Select Case UCase(cboImportType.Text)
    Case "LEDGERS"
        strXmldata = LedgerMasterText(intI)
    Case "STOCK ITEMS"
        strXmldata = StockItemMasterText(intI)
    End Select
    
    objXml.open "POST", "http://" & Trim$(txtSystemName.Text) & ":" & Trim$(txtPortNo.Text), False
    objXml.send strXmldata
    
    If InStr(1, Replace(objXml.responseText, vbCrLf, vbTab), "<LINEERROR>", vbTextCompare) <> 0 Then
        lngErrCnt = lngErrCnt + 1
        Print #lngF, "**********************************************************************"
        Print #lngF, " Line No.: " & intI & "  Name: " & Trim$(xlWS.Cells(intI, 16)) & "   " & Replace(objXml.responseText, vbCrLf, vbTab) '& vbCrLf & strXmldata
    End If
Next intI
sbExport.SimpleText = vbNullString
xlWb.Close
Screen.MousePointer = vbDefault
If lngErrCnt > 0 Then
    Print #lngF, "**********************************************************************"
    MsgBox "Process Completed with Errors." & vbCrLf & "Please refer Tally.imp file", , "Tally"
    Print #lngF, " Process Completed with Errors (Count: " & lngErrCnt & ")"
Else
    MsgBox "Process Completed", , "Tally"
End If
Print #lngF, " Completion Time: " & Format(Now, "DD-MMM-YYYY HH:MM:SS")
Print #lngF, "**********************************************************************"



ERRIMPORT:
    Set xlApp = Nothing
    Set xlWb = Nothing
    Set xlWS = Nothing
    Set objXml = Nothing
    Close #lngF
    Screen.MousePointer = vbDefault
    If Err.Number <> 0 Then
        Debug.Print Err.Description
        MsgBox Err.Number & "  " & Err.Description, , "Tally"
    End If
End Sub

Private Sub cmdFileOpen_Click()
On Error Resume Next
cdlg.DialogTitle = "Select Excel file to be exported"
cdlg.InitDir = App.Path
cdlg.Filter = "*.xls|"
cdlg.FilterIndex = 1
'cdlg.CancelError = True
cdlg.ShowOpen
txtFileName.Text = cdlg.FileName
If Dir(Trim$(txtFileName.Text)) = vbNullString Then
    MsgBox "Invalid Filename"
    txtFileName.Text = vbNullString
    Exit Sub
End If
End Sub

Private Function ReplaceXmlText(ByVal strXmlText As String) As String
    Dim strXml As String

    strXml = Replace(strXmlText, "&", "&amp;")
    strXml = Replace(strXml, "'", "&apos;")
    strXml = Replace(strXml, """", "&quot;")
    strXml = Replace(strXml, ">", "&gt;")
    strXml = Replace(strXml, "<", "&lt;")
    
    ReplaceXmlText = strXml
End Function

Private Function LedgerMasterText(ByVal intI As Integer) As String
    Dim strTemp As String
    Dim strTxt As String
    sbExport.SimpleText = intI & ": " & Trim$(xlWS.Cells(intI, 2))
    strTxt = vbNullString

    strTxt = _
    "<ENVELOPE>" & vbCrLf & _
    "<HEADER>" & vbCrLf & _
    "<VERSION>1</VERSION>" & vbCrLf & _
    "<TALLYREQUEST>Import </TALLYREQUEST>" & vbCrLf & _
    "<TYPE>Data</TYPE>" & vbCrLf & _
    "<ID>All Masters</ID>" & vbCrLf & _
    "</HEADER>" & vbCrLf & _
    "<BODY>" & vbCrLf & _
    "<DESC>" & _
    "<STATICVARIABLES>" & _
    "<SVCURRENTCOMPANY>##SVCurrentCompany</SVCURRENTCOMPANY>" & _
    "</STATICVARIABLES>" & _
    "</DESC>" & _
    "<DATA>" & vbCrLf & _
    "<TALLYMESSAGE>" & vbCrLf & _
    "<LEDGER>" & vbCrLf & _
    "<NAME.LIST>" & vbCrLf & _
    "<NAME>" & ReplaceXmlText(Trim$(xlWS.Cells(intI, 2))) & "</NAME>" & vbCrLf
    
    If Trim$(xlWS.Cells(intI, 1)) <> vbNullString Then
       strTxt = strTxt & "<NAME>" & ReplaceXmlText(Trim$(xlWS.Cells(intI, 1))) & "</NAME>" & vbCrLf
    End If
    
    strTxt = strTxt & _
    "</NAME.LIST>" & vbCrLf & _
    "<PARENT>" & ReplaceXmlText(Trim$(xlWS.Cells(intI, 3))) & "</PARENT>" & vbCrLf
    
    '-----Optional----------
    If Trim$(xlWS.Cells(intI, 4)) <> vbNullString Then
        strTxt = strTxt & "<ADDRESS.LIST>" & vbCrLf
        strTxt = strTxt & "<ADDRESS>" & ReplaceXmlText(Trim$(xlWS.Cells(intI, 4))) & "</ADDRESS>" & vbCrLf   'Address 1
        If Trim$(xlWS.Cells(intI, 5)) <> vbNullString Then strTxt = strTxt & "<ADDRESS>" & ReplaceXmlText(Trim$(xlWS.Cells(intI, 5))) & "</ADDRESS>" & vbCrLf           'Address 2
        If Trim$(xlWS.Cells(intI, 6)) <> vbNullString Then strTxt = strTxt & "<ADDRESS>" & ReplaceXmlText(Trim$(xlWS.Cells(intI, 6))) & "</ADDRESS>" & vbCrLf           'Address 3
        strTxt = strTxt & "</ADDRESS.LIST>" & vbCrLf
    End If
            
    If Trim$(xlWS.Cells(intI, 7)) <> vbNullString Then
        strTxt = strTxt & "<STATENAME>" & ReplaceXmlText(Trim$(xlWS.Cells(intI, 7))) & "</STATENAME>"
    End If
    
    If Trim$(xlWS.Cells(intI, 8)) <> vbNullString Then
        strTxt = strTxt & "<LEDGERPHONE>" & ReplaceXmlText(Trim$(xlWS.Cells(intI, 8))) & "</LEDGERPHONE>"
    End If
    
    If Trim$(xlWS.Cells(intI, 9)) <> vbNullString Then
        strTxt = strTxt & "<LEDGERFAX>" & ReplaceXmlText(Trim$(xlWS.Cells(intI, 9))) & "</LEDGERFAX>"
    End If
    
    If Trim$(xlWS.Cells(intI, 10)) <> vbNullString Then
        strTxt = strTxt & "<EMAIL>" & ReplaceXmlText(Trim$(xlWS.Cells(intI, 10))) & "</EMAIL>"
    End If
        
    strTemp = ReplaceXmlText(Trim$(xlWS.Cells(intI, 2)))
    strTxt = strTxt & "<ADDITIONALNAME>" & Trim$(strTemp) & "</ADDITIONALNAME>" & vbCrLf
    '-----Optional Ends Here----------
    
    strTxt = strTxt & _
    "</LEDGER>" & vbCrLf & _
    "</TALLYMESSAGE>" & vbCrLf & _
    "</DATA>" & vbCrLf & _
    "</BODY>" & vbCrLf & _
    "</ENVELOPE>" & vbCrLf
    
    LedgerMasterText = strTxt
    
End Function

Private Sub Form_Load()
With cboImportType
    .Clear
    .AddItem "Ledgers"
    .AddItem "Stock Items"
    .ListIndex = 1
End With


'----TEMP ---------
'cboImportType.ListIndex = 0
txtSystemName.Text = "LOCALHOST"
txtPortNo.Text = "9000"
txtFileName.Text = "D:\Documents and Settings\raghunandan.gj\My Documents\Demo\DataTrn.xls"
'--------------------------------------------------------
End Sub

Private Function StockItemMasterText(ByVal intI As Integer) As String
    
    Dim strTemp As String
    Dim strTxt As String
    sbExport.SimpleText = intI & ": " & Trim$(xlWS.Cells(intI, 1))
    
    strTxt = vbNullString
    
    strTxt = _
    "<ENVELOPE>" & vbCrLf & _
    "<HEADER>" & vbCrLf & _
    "<VERSION>1</VERSION>" & vbCrLf & _
    "<TALLYREQUEST>Import</TALLYREQUEST>" & vbCrLf & _
    "<TYPE>Data</TYPE>" & vbCrLf & _
    "<ID>All Masters</ID>" & vbCrLf & _
    "</HEADER>" & vbCrLf & _
    "<BODY>" & vbCrLf & _
    "<DESC>" & _
    "<STATICVARIABLES>" & _
    "<SVCURRENTCOMPANY>##SVCurrentCompany</SVCURRENTCOMPANY>" & _
    "</STATICVARIABLES>" & _
    "</DESC>" & _
    "<DATA>" & vbCrLf & _
    "<TALLYMESSAGE>" & vbCrLf & _
    "<STOCKITEM>" & vbCrLf & _
    "<NAME.LIST>" & vbCrLf & _
    "<NAME>" & ReplaceXmlText(Trim$(xlWS.Cells(intI, 2))) & "</NAME>" & vbCrLf & _
    "<NAME>" & ReplaceXmlText(Trim$(xlWS.Cells(intI, 1))) & "</NAME>" & vbCrLf & _
    "</NAME.LIST>" & vbCrLf & _
    "<PARENT>" & ReplaceXmlText(Trim$(xlWS.Cells(intI, 3))) & "</PARENT>" & vbCrLf & _
    "<CATEGORY/>" & vbCrLf & _
    "<BASEUNITS>" & ReplaceXmlText(Trim$(xlWS.Cells(intI, 4))) & "</BASEUNITS>" & vbCrLf & _
    "<ADDITIONALUNITS/>" & vbCrLf
    
    strTxt = strTxt & _
    "<ISBATCHWISEON>No</ISBATCHWISEON>" & vbCrLf & _
    "<HASMFGDATE>No</HASMFGDATE>" & vbCrLf & _
    "<ISPERISHABLEON>No</ISPERISHABLEON>" & vbCrLf & _
    "<COSTINGMETHOD>Avg.Cost</COSTINGMETHOD>" & vbCrLf & _
    "<OPENINGBALANCE>" & ReplaceXmlText(Trim$(xlWS.Cells(intI, 5))) & " " & ReplaceXmlText(Trim$(xlWS.Cells(intI, 4))) & "</OPENINGBALANCE>" & vbCrLf & _
    "<OPENINGVALUE>" & -1 * (Val(Trim$(xlWS.Cells(intI, 5))) * Val(Trim$(xlWS.Cells(intI, 6)))) & "</OPENINGVALUE>" & vbCrLf & _
    "<OPENINGRATE>" & ReplaceXmlText(Trim$(xlWS.Cells(intI, 6))) & "/" & ReplaceXmlText(Trim$(xlWS.Cells(intI, 4))) & "</OPENINGRATE>" & vbCrLf & _
    "<BATCHALLOCATIONS.LIST>" & vbCrLf & _
    "<NAME>Primary Batch</NAME>" & vbCrLf & _
    "<BATCHNAME>Primary Batch</BATCHNAME>" & vbCrLf & _
    "<GODOWNNAME>Main Location</GODOWNNAME>" & vbCrLf & _
    "<EXPIRYPERIOD/>" & vbCrLf & _
    "<OPENINGBALANCE>" & ReplaceXmlText(Trim$(xlWS.Cells(intI, 5))) & " " & ReplaceXmlText(Trim$(xlWS.Cells(intI, 4))) & "</OPENINGBALANCE>" & vbCrLf & _
    "<OPENINGVALUE>" & -1 * (Val(Trim$(xlWS.Cells(intI, 5))) * Val(Trim$(xlWS.Cells(intI, 6)))) & "</OPENINGVALUE>" & vbCrLf & _
    "<OPENINGRATE>" & ReplaceXmlText(Trim$(xlWS.Cells(intI, 6))) & "/" & ReplaceXmlText(Trim$(xlWS.Cells(intI, 4))) & "</OPENINGRATE>" & vbCrLf & _
    "</BATCHALLOCATIONS.LIST>" & vbCrLf & _
    "</STOCKITEM>" & vbCrLf & _
    "</TALLYMESSAGE>" & vbCrLf & _
    "</DATA>" & vbCrLf & _
    "</BODY>" & vbCrLf & _
    "</ENVELOPE>" & vbCrLf
    
    StockItemMasterText = strTxt

End Function

