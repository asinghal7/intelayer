VERSION 5.00
Begin VB.Form Create 
   Caption         =   "Create"
   ClientHeight    =   4275
   ClientLeft      =   60
   ClientTop       =   345
   ClientWidth     =   7275
   Icon            =   "Create.frx":0000
   LinkTopic       =   "Form1"
   ScaleHeight     =   4275
   ScaleWidth      =   7275
   StartUpPosition =   2  'CenterScreen
   Begin VB.ComboBox Combo2 
      Height          =   315
      Left            =   1800
      Style           =   2  'Dropdown List
      TabIndex        =   12
      Top             =   2760
      Width           =   1815
   End
   Begin VB.ComboBox Combo1 
      Height          =   315
      Left            =   1800
      Style           =   2  'Dropdown List
      TabIndex        =   11
      Top             =   2040
      Width           =   1815
   End
   Begin VB.CommandButton Command2 
      Caption         =   "EXIT"
      BeginProperty Font 
         Name            =   "Times New Roman"
         Size            =   14.25
         Charset         =   0
         Weight          =   700
         Underline       =   0   'False
         Italic          =   0   'False
         Strikethrough   =   0   'False
      EndProperty
      Height          =   495
      Left            =   3840
      TabIndex        =   10
      Top             =   3480
      Width           =   1335
   End
   Begin VB.CommandButton Command1 
      Caption         =   "POST"
      BeginProperty Font 
         Name            =   "Times New Roman"
         Size            =   14.25
         Charset         =   0
         Weight          =   700
         Underline       =   0   'False
         Italic          =   0   'False
         Strikethrough   =   0   'False
      EndProperty
      Height          =   495
      Left            =   1800
      TabIndex        =   9
      Top             =   3480
      Width           =   1695
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
      Height          =   300
      Left            =   1800
      TabIndex        =   2
      Top             =   1320
      Width           =   1020
   End
   Begin VB.TextBox Text4 
      BeginProperty DataFormat 
         Type            =   1
         Format          =   "0.0000"
         HaveTrueFalseNull=   0
         FirstDayOfWeek  =   0
         FirstWeekOfYear =   0
         LCID            =   1033
         SubFormatType   =   1
      EndProperty
      Height          =   420
      Left            =   5160
      TabIndex        =   1
      Top             =   2040
      Width           =   1260
   End
   Begin VB.TextBox Text5 
      Height          =   540
      Left            =   5160
      TabIndex        =   0
      Top             =   2640
      Width           =   1740
   End
   Begin VB.Label Label2 
      Alignment       =   2  'Center
      Caption         =   "Creation of Receipts"
      BeginProperty Font 
         Name            =   "Times New Roman"
         Size            =   18
         Charset         =   0
         Weight          =   700
         Underline       =   0   'False
         Italic          =   0   'False
         Strikethrough   =   0   'False
      EndProperty
      Height          =   495
      Left            =   1920
      TabIndex        =   8
      Top             =   240
      Width           =   3495
   End
   Begin VB.Label Label1 
      Alignment       =   2  'Center
      Caption         =   "Date"
      BeginProperty Font 
         Name            =   "Times New Roman"
         Size            =   12
         Charset         =   0
         Weight          =   400
         Underline       =   0   'False
         Italic          =   0   'False
         Strikethrough   =   0   'False
      EndProperty
      Height          =   330
      Left            =   240
      TabIndex        =   7
      Top             =   1320
      Width           =   855
   End
   Begin VB.Label Label5 
      Alignment       =   2  'Center
      Caption         =   "Amount"
      BeginProperty Font 
         Name            =   "Times New Roman"
         Size            =   12
         Charset         =   0
         Weight          =   400
         Underline       =   0   'False
         Italic          =   0   'False
         Strikethrough   =   0   'False
      EndProperty
      Height          =   330
      Left            =   3840
      TabIndex        =   6
      Top             =   2160
      Width           =   975
   End
   Begin VB.Label Label3 
      Alignment       =   2  'Center
      Caption         =   "Account"
      BeginProperty Font 
         Name            =   "Times New Roman"
         Size            =   12
         Charset         =   0
         Weight          =   400
         Underline       =   0   'False
         Italic          =   0   'False
         Strikethrough   =   0   'False
      EndProperty
      Height          =   330
      Left            =   240
      TabIndex        =   5
      Top             =   2040
      Width           =   1215
   End
   Begin VB.Label Label4 
      Alignment       =   2  'Center
      Caption         =   "Particulars"
      BeginProperty Font 
         Name            =   "Times New Roman"
         Size            =   12
         Charset         =   0
         Weight          =   400
         Underline       =   0   'False
         Italic          =   0   'False
         Strikethrough   =   0   'False
      EndProperty
      Height          =   330
      Left            =   240
      TabIndex        =   4
      Top             =   2760
      Width           =   1215
   End
   Begin VB.Label Label6 
      Alignment       =   2  'Center
      Caption         =   "Narration"
      BeginProperty Font 
         Name            =   "Times New Roman"
         Size            =   12
         Charset         =   0
         Weight          =   400
         Underline       =   0   'False
         Italic          =   0   'False
         Strikethrough   =   0   'False
      EndProperty
      Height          =   330
      Left            =   3720
      TabIndex        =   3
      Top             =   2760
      Width           =   1215
   End
End
Attribute VB_Name = "Create"
Attribute VB_GlobalNameSpace = False
Attribute VB_Creatable = False
Attribute VB_PredeclaredId = True
Attribute VB_Exposed = False
Public xmlstc As String
Public responsstr As String
Public ServerHTTP As New MSXML2.ServerXMLHTTP30
Public XMLDOM As New MSXML2.DOMDocument30
Public CHILDNODE As Object
Public I As Integer
Public ERRORSTR As String

Private Sub Command1_Click()

    Dim ComboString1 As String
    Dim ComboString2 As String
    Dim ComboString3 As String
    Dim ComboString11 As String
    Dim ComboString21 As String
    Dim ComboString31 As String
    
    ComboString11 = Combo1.Text
    ComboString21 = Combo2.Text
    ComboString31 = Text5.Text
    
    ComboString1 = Combo1.Text
    ComboString2 = Combo2.Text
    ComboString3 = Text5.Text
    
    If Combo1.Text = "" Or Combo2.Text = "" Or Text1.Text = "" Or Text4.Text = "" Then
        MsgBox "Enters All The information", vbApplicationModal, "Voucher Creation"
    Else
        date2 = Format(Text1.Text, "dd/mm/yyyy")
        'MsgBox date2
        Temp = Str$(Text4.Text * -1)
        
        If InStrRev(ComboString11, "&") Then
            ComboString1 = Replace(ComboString11, "&", "" & "")
        End If
        
        If InStrRev(ComboString21, "&") Then
            ComboString2 = Replace(ComboString21, "&", "" & "")
        End If
    
        If InStrRev(ComboString31, "&") Then
            ComboString3 = Replace(ComboString31, "&", "" & "")
        End If
    
        xmlstc = "<ENVELOPE>" + vbCrLf & _
        "<HEADER>" + vbCrLf & _
        "<VERSION>1</VERSION>" + vbCrLf & _
        "<TALLYREQUEST>Import</TALLYREQUEST>" + vbCrLf & _
        "<TYPE>Data</TYPE>" + vbCrLf & _
        "<ID>Vouchers</ID>" + vbCrLf & _
        "</HEADER>" + vbCrLf & _
        "<BODY>" + vbCrLf & _
        "<DESC>" + vbCrLf & _
        "</DESC>" + vbCrLf & _
        "<DATA>" + vbCrLf & _
        "<TALLYMESSAGE >" + vbCrLf & _
        "<VOUCHER VCHTYPE=""Receipt"" ACTION=""Create"">" + vbCrLf & _
        "<DATE>" + date2 + "</DATE>" + vbCrLf & _
        "<NARRATION>" + ComboString3 + "</NARRATION>" + vbCrLf & _
        "<VOUCHERTYPENAME>Receipt</VOUCHERTYPENAME>" + vbCrLf & _
        "<EFFECTIVEDATE>" + date2 + "</EFFECTIVEDATE>" + vbCrLf & _
        "<ALLLEDGERENTRIES.LIST>" + vbCrLf & _
        "<LEDGERNAME>" + ComboString2 + "</LEDGERNAME>" + vbCrLf & _
        "<AMOUNT>" + Text4.Text + "</AMOUNT>" + vbCrLf & _
        "</ALLLEDGERENTRIES.LIST>" + vbCrLf & _
        "<ALLLEDGERENTRIES.LIST>" + vbCrLf
        
        xmlstc = xmlstc + "<LEDGERNAME>" + ComboString1 + "</LEDGERNAME>" + vbCrLf & _
        "<ISDEEMEDPOSITIVE>Yes</ISDEEMEDPOSITIVE>" + vbCrLf & _
        "<AMOUNT>" + Temp + "</AMOUNT>" + vbCrLf & _
        "</ALLLEDGERENTRIES.LIST>" + vbCrLf & _
        "</VOUCHER>" + vbCrLf & _
        "</TALLYMESSAGE>" + vbCrLf & _
        "</DATA>" + vbCrLf & _
        "</BODY>" + vbCrLf & "</ENVELOPE>"
        'MsgBox xmlstc

        ServerHTTP.Open "POST", "http://localhost:" + PortNumber
        ServerHTTP.send xmlstc
    
        responsstr = ServerHTTP.responseText
        newstring = InStrRev(responsstr, "<LINEERROR>")
    
        If newstring = 0 Then
            XMLDOM.loadXML (responsstr)
            MsgBox "Response String " + responsstr
            Set CHILDNODE = XMLDOM.selectNodes("ENVELOPE/BODY/DATA/IMPORTRESULT/LASTVCHID")
            MsgBox "Voucher Created with MASTER ID " + CHILDNODE(0).Text, , "Voucher Creation"
           ' MsgBox "ABC Save Successful", vbOKOnly, "Voucher : "
        Else
            MsgBox "Failed to POST"
        End If
  
        responsestr = ServerHTTP.responseText

        Text4.Text = ""
        Text5.Text = ""
    End If
    
End Sub

Private Sub Command2_Click()

    Unload Create
    MAIN.Show

End Sub

Private Sub Form_Load()
    
    Text1.Enabled = False
   ' EnableCloseButton Me.hWnd, False

    Set TallyCn = New ADODB.Connection
    TallyCn.Open "TallyODBC_" & PortNumber
   
    Set rst = New ADODB.Recordset
    rst.Open "Select $Name From CashBankLedgers", TallyCn, adOpenDynamic, adLockOptimistic
          
    rst.MoveFirst
    
    Do While Not rst.EOF
        Combo1.AddItem rst.fields.Item(0)
        'List2.AddItem rst.Fields.Item(0)
        rst.MoveNext
    Loop
    
    rst.Close
    
    rst.Open "Select $Name From AccountLedgers", TallyCn, adOpenDynamic, adLockOptimistic
    rst.MoveFirst
    
    Do While Not rst.EOF
        Combo2.AddItem rst.fields.Item(0)
        'List2.AddItem rst.Fields.Item(0)

        rst.MoveNext
    Loop
    
    Text1.Text = Format$(Now, "dd/mm/yyyy")
        
End Sub

Private Sub Text1_Change()
 
    date2 = Format(Text1.Text, "dd/mm/yyyy")

End Sub

Private Sub Text4_Change()

    If Text4.Text <> "" Then
        Temp = Str$(Text4.Text * -1)
    End If

End Sub

