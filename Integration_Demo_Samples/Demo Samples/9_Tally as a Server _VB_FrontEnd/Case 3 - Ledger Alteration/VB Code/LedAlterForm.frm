VERSION 5.00
Begin VB.Form LedForm 
   Caption         =   "Form1"
   ClientHeight    =   3720
   ClientLeft      =   60
   ClientTop       =   345
   ClientWidth     =   5595
   LinkTopic       =   "Form1"
   ScaleHeight     =   3720
   ScaleWidth      =   5595
   StartUpPosition =   3  'Windows Default
   Begin VB.ComboBox CmbLed 
      Height          =   315
      Left            =   2520
      TabIndex        =   6
      Top             =   1560
      Width           =   2775
   End
   Begin VB.CommandButton Command2 
      Caption         =   "EXIT"
      BeginProperty Font 
         Name            =   "MS Sans Serif"
         Size            =   8.25
         Charset         =   0
         Weight          =   700
         Underline       =   0   'False
         Italic          =   0   'False
         Strikethrough   =   0   'False
      EndProperty
      Height          =   495
      Left            =   3600
      TabIndex        =   4
      Top             =   3000
      Width           =   1455
   End
   Begin VB.TextBox txtName 
      Height          =   375
      Left            =   2520
      TabIndex        =   3
      Top             =   2280
      Width           =   2775
   End
   Begin VB.CommandButton command1 
      Caption         =   "Alter Ledger"
      BeginProperty Font 
         Name            =   "MS Sans Serif"
         Size            =   8.25
         Charset         =   0
         Weight          =   700
         Underline       =   0   'False
         Italic          =   0   'False
         Strikethrough   =   0   'False
      EndProperty
      Height          =   495
      Left            =   480
      TabIndex        =   0
      Top             =   3000
      Width           =   2415
   End
   Begin VB.Label Label4 
      Alignment       =   2  'Center
      Caption         =   "Ledger Alteration"
      BeginProperty Font 
         Name            =   "MS Sans Serif"
         Size            =   18
         Charset         =   0
         Weight          =   700
         Underline       =   0   'False
         Italic          =   0   'False
         Strikethrough   =   0   'False
      EndProperty
      Height          =   495
      Left            =   1080
      TabIndex        =   5
      Top             =   360
      Width           =   3615
   End
   Begin VB.Label Label2 
      Caption         =   "Enter New Name"
      BeginProperty Font 
         Name            =   "MS Sans Serif"
         Size            =   8.25
         Charset         =   0
         Weight          =   700
         Underline       =   0   'False
         Italic          =   0   'False
         Strikethrough   =   0   'False
      EndProperty
      Height          =   255
      Left            =   360
      TabIndex        =   2
      Top             =   2280
      Width           =   1815
   End
   Begin VB.Label Label1 
      Caption         =   "Select Ledger"
      BeginProperty Font 
         Name            =   "MS Sans Serif"
         Size            =   8.25
         Charset         =   0
         Weight          =   700
         Underline       =   0   'False
         Italic          =   0   'False
         Strikethrough   =   0   'False
      EndProperty
      Height          =   255
      Left            =   360
      TabIndex        =   1
      Top             =   1560
      Width           =   1575
   End
End
Attribute VB_Name = "LedForm"
Attribute VB_GlobalNameSpace = False
Attribute VB_Creatable = False
Attribute VB_PredeclaredId = True
Attribute VB_Exposed = False
Dim Address  As String

Private Sub CmbLed_Click()
txtName.Text = CmbLed.Text
End Sub

Private Sub Command1_Click()

Dim xmlstr As String
Dim xmlstr1 As String

Dim ResponseStr As String
Dim ServerHTTP As New Msxml2.ServerXMLHTTP30
Dim XMLDom As New Msxml2.DOMDocument30
Dim ChildNodes As Object
Dim i As Integer
Dim errorstr As String

xmlstr = _
"<ENVELOPE>" & vbCrLf & _
"<HEADER>" & vbCrLf & _
"<VERSION>1</VERSION>" & vbCrLf & _
"<TALLYREQUEST>Import</TALLYREQUEST>" & vbCrLf & _
"<TYPE>Data</TYPE>" & vbCrLf & _
"<ID>All Masters</ID>" & vbCrLf & _
"</HEADER>" & vbCrLf & _
"<BODY>" & vbCrLf & _
"<DESC>" & vbCrLf & _
"<STATICVARIABLES>" & vbCrLf & _
"<SVEXPORTFORMAT>$$SysName:XML</SVEXPORTFORMAT>" & vbCrLf & _
"</STATICVARIABLES>" & vbCrLf & _
"</DESC>" & vbCrLf & _
"<DATA>" & vbCrLf & _
"<TALLYMESSAGE>" & vbCrLf & _
"<LEDGER NAME=""" & CmbLed.Text & """>" & vbCrLf & _
"<NAME.LIST>" & vbCrLf & _
"<NAME>" & txtName.Text & "</NAME>" & vbCrLf & _
"</NAME.LIST>" & vbCrLf & _
"</LEDGER>" & vbCrLf & _
"</TALLYMESSAGE>" & vbCrLf & _
"</DATA>" & vbCrLf & _
"</BODY>" & vbCrLf & _
"</ENVELOPE>"

MsgBox xmlstr

ServerHTTP.open "POST", Address
ServerHTTP.send xmlstr
  
ResponseStr = ServerHTTP.responseText
MsgBox ResponseStr
'--- Parse the response - Tally will return tag <LINEERROR> in case of '--- error

XMLDom.loadXML (ResponseStr)
Set ChildNodes = XMLDom.selectNodes("/RESPONSE/LINEERROR")

If (ChildNodes.length > 0) Then
    
    '--- There can be multiple <LINEERROR> tags - combine them
    For i = 0 To ChildNodes.length - 1
        errorstr = errorstr & ChildNodes(i).Text & " "
    Next
    MsgBox errorstr, vbCritical, "Error"
    
Else
    MsgBox "Save successful", vbOKOnly, "Ledger: " + LedForm.txtName.Text
End If



End Sub

Private Sub Command2_Click()
End
End Sub

Private Sub Form_Load()


Dim ResponseStr As String
Dim ServerHTTP As New Msxml2.ServerXMLHTTP30

Dim i As Integer


Dim StrRequestXML

'On Error GoTo checkerror

StrRequestXML = _
"<ENVELOPE>" & _
"<HEADER>" & _
"<VERSION>1</VERSION>" & vbCrLf & _
"<TALLYREQUEST>Export</TALLYREQUEST>" & _
"<TYPE>Data</TYPE>" & vbCrLf & _
"<ID>List of Ledgers</ID>" & vbCrLf & _
"</HEADER>" & _
"  <BODY>" & _
"      <DESC>" & _
"        <STATICVARIABLES>" & _
"          <SVEXPORTFORMAT>$$SysName:XML</SVEXPORTFORMAT>" & _
"        </STATICVARIABLES>" & _
"      </DESC>" & _
"  </BODY>" & _
"</ENVELOPE>"


Dim IPAddress As String
Dim PortNumber As String

IPAddress = InputBox("Enter IP Address", "Tally Server Address", "localhost")
PortNumber = InputBox("Enter Port Number", "Tally Servers port Number", "9000")
Address = "http://" + IPAddress + ":" + PortNumber

ServerHTTP.open "POST", Address  '"http://"LocalHost:9000"
ServerHTTP.send StrRequestXML

ResponseStr = ServerHTTP.responseText


Dim oXMLDoc
Dim oChildNodes

Set oXMLDoc = CreateObject("Microsoft.XMLDOM")
oXMLDoc.async = False
oXMLDoc.loadXML (ResponseStr)
'MsgBox ResponseStr

Set oChildNodes = oXMLDoc.selectNodes("/LISTOFLEDGERS/NAME")
   
For i = 0 To oChildNodes.length - 1
   CmbLed.AddItem (oChildNodes(i).Text)
Next

End Sub


Private Sub Frame1_DragDrop(Source As Control, X As Single, Y As Single)

End Sub

