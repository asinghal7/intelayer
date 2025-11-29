<?php


// case : if got a post string from binary
if ( isset( $HTTP_RAW_POST_DATA ) )
{ 
    // get the xml object 
    $xml_object = simplexml_load_string( $HTTP_RAW_POST_DATA );    

    // get request person name
    $request_person_name = $xml_object->REQUEST->NAME;

    // get the requested employee id 
    $request_emp_id = $xml_object->REQUEST->EMPID;

    // prepare xml response
    $res_str  =  "<ENVELOPE>";
    $res_str .=  "<HEADER>";
    $res_str .=  "<VERSION>1</VERSION>";
    $res_str .=  "<STATUS>1</STATUS>";
    $res_str .=  "</HEADER>";
    $res_str .=  "<BODY>";
    $res_str .=  "<DATA>";
    $res_str .=  "<CUSTOMER>";
    $res_str .=  "<NAME>". $request_person_name ."</NAME> ";
    $res_str .=  "<EMPID>". $request_emp_id ."</EMPID>"; 
    $res_str .=  "<PHONE>";
    $res_str .=  "<OFFICENO>080-66282559</OFFICENO> ";
    $res_str .=  "<HOMENO>011-22222222</HOMENO>"; 
    $res_str .=  "<MOBILE>990201234</MOBILE>"; 
    $res_str .=  "</PHONE>";
    $res_str .=  "<ADDRESS>";
    $res_str .=  "<ADDRLINE>C/o. Info Solutions</ADDRLINE> ";
    $res_str .=  "<ADDRLINE>Technology Street</ADDRLINE>"; 
    $res_str .=  "<ADDRLINE>Tech Info Park</ADDRLINE> ";
    $res_str .=  "</ADDRESS>";
    $res_str .=  "</CUSTOMER>";
    $res_str .=  "</DATA>";
    $res_str .=  "</BODY>";
    $res_str .=  "</ENVELOPE>";

    header( "CONTENT-LENGTH:". strlen( $res_str ) );
            print $res_str;

}
?>
