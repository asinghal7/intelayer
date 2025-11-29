VERSION 5.00
Object = "{5E9E78A0-531B-11CF-91F6-C2863C385E30}#1.0#0"; "msflxgrd.ocx"
Begin VB.Form FlexGrid 
   Caption         =   "Report"
   ClientHeight    =   5850
   ClientLeft      =   60
   ClientTop       =   345
   ClientWidth     =   10650
   LinkTopic       =   "Form2"
   ScaleHeight     =   5850
   ScaleWidth      =   10650
   StartUpPosition =   1  'CenterOwner
   Begin VB.CommandButton Command1 
      Caption         =   "EXIT"
      BeginProperty Font 
         Name            =   "MS Sans Serif"
         Size            =   12
         Charset         =   0
         Weight          =   700
         Underline       =   0   'False
         Italic          =   0   'False
         Strikethrough   =   0   'False
      EndProperty
      Height          =   615
      Left            =   4200
      TabIndex        =   1
      Top             =   4920
      Width           =   1575
   End
   Begin MSFlexGridLib.MSFlexGrid MSFlexGrid1 
      Height          =   3495
      Left            =   600
      TabIndex        =   0
      Top             =   1080
      Width           =   9255
      _ExtentX        =   16325
      _ExtentY        =   6165
      _Version        =   393216
      FocusRect       =   0
      AllowUserResizing=   3
   End
   Begin VB.Label Label1 
      Alignment       =   2  'Center
      Caption         =   "BILL WISE DETAILS"
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
      TabIndex        =   2
      Top             =   360
      Width           =   5655
   End
End
Attribute VB_Name = "FlexGrid"
Attribute VB_GlobalNameSpace = False
Attribute VB_Creatable = False
Attribute VB_PredeclaredId = True
Attribute VB_Exposed = False
Private Sub Command1_Click()
Unload Me
ODBCMAIN.Show
End Sub

Private Sub Form_Load()

    MSFlexGrid1.Cols = 9
    MSFlexGrid1.Rows = 15
    
    MSFlexGrid1.ColWidth(0) = 0
    MSFlexGrid1.TextMatrix(0, 1) = "Bill Number"
     MSFlexGrid1.ColWidth(1) = 2000
      
    MSFlexGrid1.TextMatrix(0, 2) = "Bill Date"
    MSFlexGrid1.ColWidth(2) = 2000
    MSFlexGrid1.TextMatrix(0, 3) = "Ledger Name"
        MSFlexGrid1.ColWidth(3) = 2000
    MSFlexGrid1.TextMatrix(0, 4) = "Pending Amount"
        MSFlexGrid1.ColWidth(4) = 2000
    MSFlexGrid1.TextMatrix(0, 5) = "Voucher Type"
        MSFlexGrid1.ColWidth(5) = 2000
    MSFlexGrid1.TextMatrix(0, 6) = "Voucher Number"
            MSFlexGrid1.ColWidth(6) = 2000
    MSFlexGrid1.TextMatrix(0, 7) = "Voucher Amount"
            MSFlexGrid1.ColWidth(7) = 2000
            
    MSFlexGrid1.TextMatrix(0, 8) = "Item Details"
            MSFlexGrid1.ColWidth(8) = 5000
    
   Dim sServer As String
Dim sUser As String
Dim sPWD As String
Dim sDatabase As String

Dim DBcon As New ADODB.Connection
Dim objCmd As New ADODB.Command

Dim objRs As New ADODB.Recordset
    
    
    DBcon.CursorLocation = adUseClient
    
    DBcon.Open "TallyODBC_" & ODBCMAIN.TxtPortNo.Text
        objCmd.ActiveConnection = DBcon
    objCmd.CommandType = adCmdStoredProc
     objCmd.CommandText = "_PartyBills"
    objCmd.CreateParameter (ODBCMAIN.CmbLedger.Text)

    Set objRs = objCmd.Execute                       ' objCmd.Execute for no resultset
   
   i = 1
   While objRs.EOF = False
   MSFlexGrid1.TextMatrix(i, 1) = objRs.Fields(0) & ""
   MSFlexGrid1.TextMatrix(i, 2) = objRs.Fields(1) & ""
   MSFlexGrid1.TextMatrix(i, 3) = objRs.Fields(2) & ""
   MSFlexGrid1.TextMatrix(i, 4) = objRs.Fields(3) & ""
   MSFlexGrid1.TextMatrix(i, 5) = objRs.Fields(4) & ""
   MSFlexGrid1.TextMatrix(i, 6) = objRs.Fields(5) & ""
   MSFlexGrid1.TextMatrix(i, 7) = objRs.Fields(6) & ""
   MSFlexGrid1.TextMatrix(i, 8) = objRs.Fields(7) & ""
      
    i = i + 1
objRs.MoveNext
Wend


    Set objRs.ActiveConnection = Nothing
    Set objCmd = Nothing
    DBcon.Close
    


End Sub

