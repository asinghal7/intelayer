VERSION 5.00
Begin VB.Form MAIN 
   Caption         =   "Receipts Creation/Alteration"
   ClientHeight    =   2700
   ClientLeft      =   60
   ClientTop       =   345
   ClientWidth     =   4890
   Icon            =   "MAIN.frx":0000
   LinkTopic       =   "Form1"
   ScaleHeight     =   2700
   ScaleWidth      =   4890
   StartUpPosition =   2  'CenterScreen
   Begin VB.CommandButton Cmd_Create 
      Caption         =   "CREATE"
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
      Left            =   480
      TabIndex        =   0
      Top             =   1320
      Width           =   1695
   End
   Begin VB.CommandButton Cmd_Alter 
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
      Left            =   480
      TabIndex        =   1
      Top             =   2040
      Width           =   1695
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
      Left            =   2640
      TabIndex        =   3
      Top             =   1560
      Width           =   1695
   End
   Begin VB.Label Label1 
      Alignment       =   2  'Center
      Caption         =   "Voucher Entry for Receipts"
      BeginProperty Font 
         Name            =   "Times New Roman"
         Size            =   18
         Charset         =   0
         Weight          =   700
         Underline       =   0   'False
         Italic          =   0   'False
         Strikethrough   =   0   'False
      EndProperty
      Height          =   615
      Left            =   120
      TabIndex        =   2
      Top             =   360
      Width           =   4575
   End
End
Attribute VB_Name = "MAIN"
Attribute VB_GlobalNameSpace = False
Attribute VB_Creatable = False
Attribute VB_PredeclaredId = True
Attribute VB_Exposed = False
Private Sub Cmd_Alter_Click()

    Me.Hide
    Alter.Show
    
End Sub

Private Sub Cmd_Create_Click()

    Me.Hide
    Create.Show
    
End Sub

Private Sub Cmd_Exit_Click()

    End
    
End Sub

Private Sub Form_Load()

    MsgBox "Please ensure that Tally is Running", vbInformation, "Tally"
    Do While PortNumber = ""
        PortNumber = InputBox("Enter Port Number on which Tally is active ", "Tally", 9000)
    Loop
   ' EnableCloseButton Me.hWnd, False
    mkm = DisableCloseButton(MAIN)
End Sub

