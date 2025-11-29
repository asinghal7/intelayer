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


    // get the requested employee Office no
    $request_off_no = $xml_object->REQUEST->OFFICENO;

    // prepare xml response
    print ("<CUSTOMER>" );
    print ("<NAME>". $request_person_name ."</NAME> " );
    print ("<EMPID>". $request_emp_id ."</EMPID>" ); 
    print ("<PHONE>" );
    print ("<OFFICENO>". $request_off_no ."</OFFICENO> " );
    print ("<HOMENO>011-22222222</HOMENO>" ); 
    print ("<MOBILE>990201234</MOBILE>" ); 
    print ("</PHONE>" );
    print ("<ADDRESS>" );
    print ("<ADDRLINE>C/o. Info Solutions</ADDRLINE> " );
    print ("<ADDRLINE>Technology Street</ADDRLINE>" ); 
    print ("<ADDRLINE>Tech Info Park</ADDRLINE> " );
    print ("</ADDRESS>" );
    print ("</CUSTOMER>" );
}
?>
