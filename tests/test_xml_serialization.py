import os
import sys
import unittest
import xml.dom.minidom

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))
import obkey2.classes as classes


class TestXMLSerialization(unittest.TestCase):
    def test_xml_escape_in_deparse(self):
        action = type('A', (), {'options': {'test': 'A & B < C'}})()
        od = classes.OCString('test', 'default')
        node = od.deparse(action)
        self.assertEqual(node.toxml(), '<test>A &amp; B &lt; C</test>')

    def test_save_serialization_escapes_chain_quit_key(self):
        keyboard = classes.OBKeyboard(
            xml.dom.minidom.parseString(
                '<keyboard><chainQuitKey>A &amp; B</chainQuitKey></keyboard>'
            ).documentElement
        )
        xml_text = classes.fixed_toprettyxml(keyboard.deparse(), '  ', '  ')
        parsed = xml.dom.minidom.parseString(xml_text)
        chain_quit = parsed.documentElement.getElementsByTagName('chainQuitKey')[0]
        self.assertEqual(chain_quit.firstChild.nodeValue, 'A & B')
        self.assertIn('&amp;', xml_text)
