VERSION 5.00
Begin VB.Form ODBCMAIN 
   Caption         =   " Tally"
   ClientHeight    =   4560
   ClientLeft      =   60
   ClientTop       =   345
   ClientWidth     =   8160
   Icon            =   "ODBCMAIN.frx":0000
   LinkTopic       =   "Form1"
   MaxButton       =   0   'False
   Moveable        =   0   'False
   ScaleHeight     =   4560
   ScaleWidth      =   8160
   StartUpPosition =   2  'CenterScreen
   Begin VB.ComboBox CmbLedger 
      Height          =   315
      ItemData        =   "ODBCMAIN.frx":030A
      Left            =   3240
      List            =   "ODBCMAIN.frx":030C
      Style           =   2  'Dropdown List
      TabIndex        =   1
      Top             =   2880
      Width           =   4095
   End
   Begin VB.TextBox TxtPortNo 
      Height          =   405
      Left            =   3240
      TabIndex        =   0
      Top             =   2280
      Width           =   1455
   End
   Begin VB.CommandButton Cmd_Exit 
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
      Left            =   3240
      TabIndex        =   4
      Top             =   3720
      Width           =   1695
   End
   Begin VB.CommandButton Cmd_Alter 
      Caption         =   "REPORT"
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
      Left            =   1560
      TabIndex        =   3
      Top             =   3720
      Width           =   1695
   End
   Begin VB.Label Label3 
      Caption         =   "Select the Ledger"
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
      Left            =   600
      TabIndex        =   6
      Top             =   2880
      Width           =   2175
   End
   Begin VB.Label Label2 
      Caption         =   "Port Number"
      BeginProperty Font 
         Name            =   "Times New Roman"
         Size            =   12
         Charset         =   0
         Weight          =   700
         Underline       =   0   'False
         Italic          =   0   'False
         Strikethrough   =   0   'False
      EndProperty
      Height          =   375
      Left            =   600
      TabIndex        =   5
      Top             =   2400
      Width           =   1935
   End
   Begin VB.Label Label1 
      Alignment       =   2  'Center
      Caption         =   "TALLY PROCEDURE"
      BeginProperty Font 
         Name            =   "MS Sans Serif"
         Size            =   24
         Charset         =   0
         Weight          =   700
         Underline       =   0   'False
         Italic          =   0   'False
         Strikethrough   =   0   'False
      EndProperty
      Height          =   975
      Left            =   240
      TabIndex        =   2
      Top             =   600
      Width           =   7095
   End
End
Attribute VB_Name = "ODBCMAIN"
Attribute VB_GlobalNameSpace = False
Attribute VB_Creatable = False
Attribute VB_PredeclaredId = True
Attribute VB_Exposed = False



Private Sub CmbLedger_DropDown()
CmbLedger.Clear
If TxtPortNo.Text = "" Then

  MsgBox "Enter Valid Port Number"
  TxtPortNo.SetFocus

Else
 
    MyConnection
  If Not Flag Then
    
  
  Set rst = New ADODB.Recordset
    rst.Open "Select $Name From Ledger", TallyCn, adOpenDynamic, adLockOptimistic
    rst.MoveFirst
    Do While Not rst.EOF
        CmbLedger.AddItem rst(0)
        rst.MoveNext
    Loop
   End If
    End If
End Sub

Private Sub CmbLedger_GotFocus()
MyConnection
   If TxtPortNo.Text = "" Then
         Cmd_Create.Enabled = False
        Cmd_Alter.Enabled = False
        Cmd_Delete.Enabled = False
        CmbLedger.Clear
    End If
   
If TxtPortNo.Text <> "" Then
    CmbLedger.Clear
    Set rst = New ADODB.Recordset
    rst.Open "Select $Name From Ledger", TallyCn, adOpenDynamic, adLockOptimistic
    rst.MoveFirst
    Do While Not rst.EOF
        CmbLedger.AddItem rst(0)
        rst.MoveNext
    Loop
        
        rst.Close
        TallyCn.Close
       
    
End If

End Sub

Private Sub Cmd_Alter_Click()
If CmbLedger.Text = "" Or TxtPortNo.Text = "" Then
    MsgBox "Select Valid Ledger/Port Number"
 Else
  
    Me.Hide
      
   
    
    FlexGrid.Show
End If
End Sub

Private Sub Cmd_Exit_Click()
End
End Sub

Private Sub Form_Load()
  ' EnableCloseButton Me.hWnd, False
 
 
     
End Sub

