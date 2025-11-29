VERSION 5.00
Begin VB.Form Main 
   Caption         =   "Main"
   ClientHeight    =   7065
   ClientLeft      =   60
   ClientTop       =   345
   ClientWidth     =   9375
   LinkTopic       =   "Form1"
   ScaleHeight     =   7065
   ScaleWidth      =   9375
   StartUpPosition =   3  'Windows Default
   Begin VB.ComboBox CmbLedger 
      Height          =   315
      Left            =   2280
      TabIndex        =   1
      Text            =   "Combo1"
      Top             =   3240
      Width           =   3015
   End
   Begin VB.CommandButton Command1 
      Caption         =   "Command1"
      Height          =   975
      Left            =   2760
      TabIndex        =   0
      Top             =   1440
      Width           =   4455
   End
End
Attribute VB_Name = "Main"
Attribute VB_GlobalNameSpace = False
Attribute VB_Creatable = False
Attribute VB_PredeclaredId = True
Attribute VB_Exposed = False
Private Sub Command1_Click()

Dim sServer As String
Dim sUser As String
Dim sPWD As String
Dim sDatabase As String

Dim DBcon As New ADODB.Connection
Dim objCmd As New ADODB.Command

Dim objRs As New ADODB.Recordset
    
    
    DBcon.CursorLocation = adUseClient
    DBcon.Open "TallyODBC_4050"
    
'MSFlexGrid1.TextMatrix(0, 0) = "Assets"
    'MSFlexGrid1.ColWidth(0) = 2000
        
    MSFlexGrid1.TextMatrix(0, 1) = "Amount"
    
    MSFlexGrid1.TextMatrix(0, 2) = "Liabilities"
    'MSFlexGrid1.ColWidth(2) = 2000
    
    MSFlexGrid1.TextMatrix(0, 3) = "Amount"
    
    objCmd.ActiveConnection = DBcon
    objCmd.CommandType = adCmdStoredProc
    objCmd.CommandText = "_LEds"
    objCmd.CreateParameter ("Sundry Debtors")
  '  objCmd.CommandText = "_GetCurrentCompany"
    Set objRs = objCmd.Execute                       ' objCmd.Execute for no resultset
   
   i = 1
   While objRs.EOF = False
   MSFlexGrid1.TextMatrix(i, 1) = objRs.Fields(0)
    i = i + 1
CmbLedger.AddItem objRs.Fields(0)
objRs.MoveNext
Wend


    Set objRs.ActiveConnection = Nothing
    Set objCmd = Nothing
    DBcon.Close


End Sub

Private Sub Main_Click()

End Sub

