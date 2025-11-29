VERSION 5.00
Begin VB.Form Alter 
   Caption         =   "Alter"
   ClientHeight    =   6795
   ClientLeft      =   60
   ClientTop       =   345
   ClientWidth     =   8535
   HasDC           =   0   'False
   Icon            =   "Final.frx":0000
   LinkTopic       =   "Form1"
   ScaleHeight     =   6795
   ScaleWidth      =   8535
   StartUpPosition =   2  'CenterScreen
   Begin VB.CommandButton Command3 
      Caption         =   "REFRESH"
      BeginProperty Font 
         Name            =   "Times New Roman"
         Size            =   12
         Charset         =   0
         Weight          =   700
         Underline       =   0   'False
         Italic          =   0   'False
         Strikethrough   =   0   'False
      EndProperty
      Height          =   495
      Left            =   3600
      TabIndex        =   4
      Top             =   5880
      Width           =   1455
   End
   Begin VB.ListBox List8 
      Height          =   1230
      Left            =   13200
      TabIndex        =   26
      Top             =   4560
      Width           =   975
   End
   Begin VB.ListBox List7 
      Height          =   1230
      Left            =   12240
      TabIndex        =   25
      Top             =   4560
      Width           =   975
   End
   Begin VB.ListBox List6 
      Height          =   1230
      Left            =   11280
      TabIndex        =   24
      Top             =   4560
      Width           =   975
   End
   Begin VB.ListBox List5 
      Height          =   1230
      Left            =   13200
      TabIndex        =   23
      Top             =   3240
      Width           =   975
   End
   Begin VB.ListBox List4 
      BeginProperty DataFormat 
         Type            =   0
         Format          =   "dd-MMM-yyyy"
         HaveTrueFalseNull=   0
         FirstDayOfWeek  =   0
         FirstWeekOfYear =   0
         LCID            =   1033
         SubFormatType   =   0
      EndProperty
      Height          =   1230
      Left            =   12360
      TabIndex        =   22
      Top             =   3240
      Width           =   855
   End
   Begin VB.TextBox Text7 
      Height          =   420
      Left            =   2280
      TabIndex        =   21
      ToolTipText     =   "ALTER ID"
      Top             =   1920
      Width           =   1620
   End
   Begin VB.TextBox Text6 
      Height          =   420
      Left            =   4200
      TabIndex        =   20
      Top             =   1920
      Width           =   1620
   End
   Begin VB.ListBox List3 
      Height          =   1230
      Left            =   11400
      TabIndex        =   19
      Top             =   3240
      Width           =   975
   End
   Begin VB.ListBox List2 
      Height          =   1230
      Left            =   10440
      TabIndex        =   18
      Top             =   3240
      Width           =   975
   End
   Begin VB.CommandButton Command2 
      Caption         =   "EXIT"
      BeginProperty Font 
         Name            =   "Times New Roman"
         Size            =   12
         Charset         =   0
         Weight          =   700
         Underline       =   0   'False
         Italic          =   0   'False
         Strikethrough   =   0   'False
      EndProperty
      Height          =   495
      Left            =   5640
      TabIndex        =   5
      Top             =   5880
      Width           =   1455
   End
   Begin VB.CommandButton Command1 
      Caption         =   "ALTER"
      BeginProperty Font 
         Name            =   "Times New Roman"
         Size            =   12
         Charset         =   0
         Weight          =   700
         Underline       =   0   'False
         Italic          =   0   'False
         Strikethrough   =   0   'False
      EndProperty
      Height          =   495
      Left            =   1320
      TabIndex        =   3
      Top             =   5880
      Width           =   1575
   End
   Begin VB.TextBox Text5 
      Height          =   780
      Left            =   6000
      TabIndex        =   2
      Top             =   4680
      Width           =   2220
   End
   Begin VB.TextBox Text4 
      BeginProperty DataFormat 
         Type            =   1
         Format          =   "d-MMM-yyyy"
         HaveTrueFalseNull=   0
         FirstDayOfWeek  =   0
         FirstWeekOfYear =   0
         LCID            =   1033
         SubFormatType   =   3
      EndProperty
      Height          =   540
      Left            =   6000
      TabIndex        =   1
      Top             =   3600
      Width           =   1620
   End
   Begin VB.TextBox Text3 
      Height          =   540
      Left            =   2280
      TabIndex        =   12
      Top             =   4560
      Width           =   1620
   End
   Begin VB.TextBox Text2 
      Height          =   540
      Left            =   2280
      TabIndex        =   10
      Top             =   3600
      Width           =   1620
   End
   Begin VB.TextBox Text1 
      BeginProperty DataFormat 
         Type            =   1
         Format          =   "d/MM/yyyy"
         HaveTrueFalseNull=   0
         FirstDayOfWeek  =   0
         FirstWeekOfYear =   0
         LCID            =   1033
         SubFormatType   =   3
      EndProperty
      Height          =   420
      Left            =   6000
      TabIndex        =   7
      Top             =   1920
      Width           =   1620
   End
   Begin VB.ListBox List1 
      Height          =   1425
      Left            =   480
      MousePointer    =   2  'Cross
      TabIndex        =   0
      ToolTipText     =   "MASTER ID"
      Top             =   1920
      Width           =   1455
   End
   Begin VB.Label Label9 
      Alignment       =   2  'Center
      Caption         =   "Alteration of Receipts"
      BeginProperty Font 
         Name            =   "Times New Roman"
         Size            =   20.25
         Charset         =   0
         Weight          =   700
         Underline       =   0   'False
         Italic          =   0   'False
         Strikethrough   =   0   'False
      EndProperty
      Height          =   615
      Left            =   1320
      TabIndex        =   17
      Top             =   360
      Width           =   5415
   End
   Begin VB.Label Label8 
      Alignment       =   2  'Center
      Caption         =   "Master ID"
      BeginProperty Font 
         Name            =   "Times New Roman"
         Size            =   11.25
         Charset         =   0
         Weight          =   400
         Underline       =   0   'False
         Italic          =   0   'False
         Strikethrough   =   0   'False
      EndProperty
      Height          =   285
      Left            =   480
      TabIndex        =   16
      Top             =   1440
      Width           =   1575
   End
   Begin VB.Label Label7 
      Alignment       =   2  'Center
      Caption         =   "Alter ID"
      BeginProperty Font 
         Name            =   "Times New Roman"
         Size            =   11.25
         Charset         =   0
         Weight          =   400
         Underline       =   0   'False
         Italic          =   0   'False
         Strikethrough   =   0   'False
      EndProperty
      Height          =   330
      Left            =   2400
      TabIndex        =   15
      Top             =   1440
      Width           =   1215
   End
   Begin VB.Label Label6 
      Alignment       =   2  'Center
      Caption         =   "Narration"
      BeginProperty Font 
         Name            =   "Times New Roman"
         Size            =   11.25
         Charset         =   0
         Weight          =   400
         Underline       =   0   'False
         Italic          =   0   'False
         Strikethrough   =   0   'False
      EndProperty
      Height          =   330
      Left            =   4080
      TabIndex        =   14
      Top             =   4680
      Width           =   1575
   End
   Begin VB.Label Label5 
      Alignment       =   2  'Center
      Caption         =   "Amount"
      BeginProperty Font 
         Name            =   "Times New Roman"
         Size            =   11.25
         Charset         =   0
         Weight          =   400
         Underline       =   0   'False
         Italic          =   0   'False
         Strikethrough   =   0   'False
      EndProperty
      Height          =   405
      Left            =   4080
      TabIndex        =   13
      Top             =   3720
      Width           =   1575
   End
   Begin VB.Label Label4 
      Alignment       =   2  'Center
      Caption         =   "Particulars"
      BeginProperty Font 
         Name            =   "Times New Roman"
         Size            =   11.25
         Charset         =   0
         Weight          =   400
         Underline       =   0   'False
         Italic          =   0   'False
         Strikethrough   =   0   'False
      EndProperty
      Height          =   450
      Left            =   360
      TabIndex        =   11
      Top             =   4680
      Width           =   1710
   End
   Begin VB.Label Label3 
      Alignment       =   2  'Center
      Caption         =   "Account"
      BeginProperty Font 
         Name            =   "Times New Roman"
         Size            =   11.25
         Charset         =   0
         Weight          =   400
         Underline       =   0   'False
         Italic          =   0   'False
         Strikethrough   =   0   'False
      EndProperty
      Height          =   450
      Left            =   480
      TabIndex        =   9
      Top             =   3720
      Width           =   1470
   End
   Begin VB.Label Label2 
      Alignment       =   2  'Center
      Caption         =   "Date"
      BeginProperty Font 
         Name            =   "Times New Roman"
         Size            =   11.25
         Charset         =   0
         Weight          =   400
         Underline       =   0   'False
         Italic          =   0   'False
         Strikethrough   =   0   'False
      EndProperty
      Height          =   330
      Left            =   6000
      TabIndex        =   8
      Top             =   1440
      Width           =   1575
   End
   Begin VB.Label Label1 
      Alignment       =   2  'Center
      Caption         =   "Voucher Number"
      BeginProperty Font 
         Name            =   "Times New Roman"
         Size            =   11.25
         Charset         =   0
         Weight          =   400
         Underline       =   0   'False
         Italic          =   0   'False
         Strikethrough   =   0   'False
      EndProperty
      Height          =   330
      Left            =   3960
      TabIndex        =   6
      Top             =   1440
      Width           =   1935
   End
End
Attribute VB_Name = "Alter"
Attribute VB_GlobalNameSpace = False
Attribute VB_Creatable = False
Attribute VB_PredeclaredId = True
Attribute VB_Exposed = False
Public xmlstc As String
Public responsstr As String
Public ServerHTTP As New MSXML2.ServerXMLHTTP30
Public I As Integer

Private Sub Command1_Click()

    Dim ComboString1 As String
    Dim ComboString2 As String
    Dim ComboString3 As String
    Dim ComboString11 As String
    Dim ComboString21 As String
    Dim ComboString31 As String
    
    ComboString11 = Text2.Text
    ComboString21 = Text3.Text
    ComboString31 = Text5.Text
    
    ComboString1 = Text2.Text
    ComboString2 = Text3.Text
    ComboString3 = Text5.Text

    If InStrRev(ComboString11, "&") Then
        ComboString1 = Replace(ComboString11, "&", "" & "")
    End If
    
    If InStrRev(ComboString21, "&") Then
        ComboString2 = Replace(ComboString21, "&", "" & "")
    End If
    
    If InStrRev(ComboString31, "&") Then
        ComboString3 = Replace(ComboString31, "&", "" & "")
    End If
    
    date2 = Format(Text1.Text, "dd-mmm-yyyy")
    
    If Text4.Text = "" Then
        MsgBox ("Please enter some value")
        Text4.SetFocus
    Else
        Temp = Str$(Text4.Text * -1)
    
        xmlstc = _
        "<ENVELOPE>" + vbCrLf & _
        "<HEADER>" + vbCrLf & _
        "<VERSION>1</VERSION>" & _
        "<TALLYREQUEST>Import</TALLYREQUEST>" + vbCrLf & _
        "<TYPE>Data</TYPE>" + vbCrLf & _
        "<ID>Vouchers</ID>" + vbCrLf & _
        "</HEADER>" + vbCrLf & _
        "<BODY>" + vbCrLf & _
        "<DESC>" + vbCrLf & _
        "</DESC>" + vbCrLf & _
        "<DATA>" + vbCrLf & _
        "<TALLYMESSAGE>" + vbCrLf & _
        "<VOUCHER DATE=" + """" + date2 + """" + " TAGNAME=""MASTER ID"" TAGVALUE=" + """" + List1.Text + """" + " ACTION=""Alter"" VCHTYPE = ""Receipt"">" + vbCrLf
        
        xmlstc = xmlstc & _
        "<ALLLEDGERENTRIES.LIST>" + vbCrLf & _
        "<LEDGERNAME>" + ComboString2 + "</LEDGERNAME>" + vbCrLf & _
        "<AMOUNT>" + Text4.Text + "</AMOUNT>" + vbCrLf & _
        "</ALLLEDGERENTRIES.LIST>" + vbCrLf & _
        "<ALLLEDGERENTRIES.LIST>" + vbCrLf & _
        "<LEDGERNAME>" + ComboString1 + "</LEDGERNAME>" + vbCrLf & _
        "<ISDEEMEDPOSITIVE>Yes</ISDEEMEDPOSITIVE>" + vbCrLf & _
        "<AMOUNT>" + Temp + "</AMOUNT>" + vbCrLf & _
        "</ALLLEDGERENTRIES.LIST>" + vbCrLf & _
        "<NARRATION>" + ComboString3 + "</NARRATION>" + vbCrLf & _
        "</VOUCHER>" + vbCrLf & _
        "</TALLYMESSAGE>" + vbCrLf & _
        "</DATA>" + vbCrLf & _
        "</BODY>" + vbCrLf & _
        "</ENVELOPE>"
        
        'MsgBox xmlstc
        WriteLog (xmlstc)
    
        ServerHTTP.Open "POST", "http://localhost:" + PortNumber
        ServerHTTP.send xmlstc
        
        responsstr = ServerHTTP.responseText
    
        newstring = InStrRev(responsstr, "<LINEERROR>")
        
        If newstring = 0 Then
            MsgBox "Save Successful", vbOKOnly, "Voucher : "
        Else
            MsgBox responsstr
            MsgBox "Failed to POST"
        End If
      
        Text1.Text = ""
        Text2.Text = ""
        Text3.Text = ""
        Text4.Text = ""
        Text5.Text = ""
        Text6.Text = ""
        Text7.Text = ""
    End If

End Sub

Private Sub Command2_Click()
    
    Unload Alter
    MAIN.Show

End Sub

Private Sub Command3_Click()

    List1.Clear
    List2.Clear
    List3.Clear
    List4.Clear
    List5.Clear
    List6.Clear
    List7.Clear
    List8.Clear
    Text1.Text = ""
    Text2.Text = ""
    Text3.Text = ""
    Text4.Text = ""
    Text5.Text = ""
    Text6.Text = ""
    Text7.Text = ""
    
    Dim rs As ADODB.Recordset
  
    Set TallyCn = New ADODB.Connection
    TallyCn.Open "TallyODBC_" & PortNumber
   
    Set rst = New ADODB.Recordset
    rst.Open "Select $MasterID, $VoucherNumber, $AlterID, $Date, $_AccountName, $_ParticularsName, $_ParticularsAmount, $Narration From Vouchers", TallyCn, adOpenDynamic, adLockOptimistic
    'On Error GoTo Err
       
    rst.MoveFirst
    
    Do While Not rst.EOF
       
        List1.AddItem rst.fields.Item(0)
        List2.AddItem rst.fields.Item(1)
        List3.AddItem rst.fields.Item(2)
        List4.AddItem rst.fields.Item(3)
        List5.AddItem rst.fields.Item(4)
        List6.AddItem rst.fields.Item(5)
        List7.AddItem rst.fields.Item(6)
        List8.AddItem rst.fields.Item(7) & ""

        rst.MoveNext
        
    Loop

    'Err:
     
     'MsgBox "No Records"
    'End

End Sub

Private Sub Form_Load()

   ' EnableCloseButton Me.hWnd, False
     
    'Label7.Visible = False
    'Label8.Visible = False
    
    List2.Visible = False
    List3.Visible = False
    List4.Visible = False
    List5.Visible = False
    List6.Visible = False
    List7.Visible = False
    List8.Visible = False
    
    Text1.Enabled = False
    Text2.Enabled = False
    Text3.Enabled = False
    Text6.Enabled = False
    Text7.Enabled = False

    Dim rs As ADODB.Recordset
       
    Set TallyCn = New ADODB.Connection
    TallyCn.Open "TallyODBC_" & PortNumber

    Set rst = New ADODB.Recordset
    rst.Open "Select $MasterID, $VoucherNumber, $AlterID, $Date, $_AccountName, $_ParticularsName, $_ParticularsAmount, $Narration From Vouchers", TallyCn, adOpenDynamic, adLockOptimistic
     
    On Error GoTo Err
    
    rst.MoveFirst

    Do While Not rst.EOF
    
        List1.AddItem rst.fields.Item(0)
        List2.AddItem rst.fields.Item(1)
        List3.AddItem rst.fields.Item(2)
        List4.AddItem rst.fields.Item(3)
        List5.AddItem rst.fields.Item(4)
        List6.AddItem rst.fields.Item(5)
        List7.AddItem rst.fields.Item(6)
        List8.AddItem rst.fields.Item(7) & ""
        
        List1.Visible = True
        List2.Visible = True
        List3.Visible = True
        List4.Visible = True
        List5.Visible = True
        List6.Visible = True
        List7.Visible = True
        List8.Visible = True
        
        rst.MoveNext
            
    Loop
    
Err:
    
    If Err.Number = 3021 Then
    
        MsgBox "No Receipts or TCP is attached to Tally"
        End
        
    End If

End Sub

Private Sub List1_Click()

    Label7.Visible = True
    Label8.Visible = True
    
    'List2.Visible = True
    'List3.Visible = True
    
    Text6.Text = List2.List(List1.ListIndex)
    Text7.Text = List3.List(List1.ListIndex)
    Text1.Text = List4.List(List1.ListIndex)
    Text2.Text = List5.List(List1.ListIndex)
    Text3.Text = List6.List(List1.ListIndex)
    Text4.Text = List7.List(List1.ListIndex)
    Text5.Text = List8.List(List1.ListIndex)

End Sub


Private Sub Text4_Change()

    If Text4.Text <> "" Then
        Temp = Str$(Text4.Text * -1)
    End If

End Sub

Public Sub WriteLog(ByVal msg As String)

Dim objFSO
Dim strFilePath As String

Set objFSO = CreateObject("Scripting.FileSystemObject")
strFilePath = objFSO.GetSpecialFolder(1) & "\" 'SYSTEM32-Folder
strFilePath = strFilePath & "debugfile.txt"

Open strFilePath For Append As #12
Print #12, "[" & Now & "] -> " & msg
Close #12

End Sub

