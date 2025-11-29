Attribute VB_Name = "ODBCModule"
Public Flag As Boolean
Public TallyCn As ADODB.Connection


Public Function MyConnection()


If ODBCMAIN.TxtPortNo.Text = "" Then
    MsgBox "Enter the Port No. "
    ODBCMAIN.TxtPortNo.SetFocus
Else
    On Error GoTo ErrDes1
    Set TallyCn = New ADODB.Connection
    TallyCn.Open "TallyODBC_" & ODBCMAIN.TxtPortNo.Text
     Flag = False
End If
   
ErrDes1:
    If Err.Number = -2147467259 Then
          MsgBox "Tally is not opened / Company is not selected / Port Number Mismatch "
         ODBCMAIN.TxtPortNo.Text = ""
          ODBCMAIN.TxtPortNo.SetFocus
          Flag = True
          
         
    'Else
     '   MsgBox Err.Description
   End If
   
   
End Function
