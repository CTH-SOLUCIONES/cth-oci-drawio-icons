"""stencil.py: path translation, compact arc flags and refusal of anything it cannot draw faithfully."""
import base64
import unittest
import zlib

from support import load_catalog  # first: puts scripts/ on sys.path

import stencil  # noqa: E402


def svg(*paths: str, view_box="0 0 42 42") -> str:
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{view_box}">' + "".join(paths) + "</svg>")


def decode(compressed: str) -> str:
    return zlib.decompress(base64.b64decode(compressed), -15).decode()


class TokenTest(unittest.TestCase):
    def test_compact_arc_flags_are_single_characters(self):
        # SVGO writes `a2 2 0 012 2`: flags 0 and 1, then 2 2
        self.assertEqual(list(stencil._tokens("a2 2 0 012 2")), ["a", "2", "2", "0", "0", "1", "2", "2"])

    def test_numbers_may_be_glued_by_signs_and_dots(self):
        self.assertEqual(list(stencil._tokens("M1.5-2.5.5.25")), ["M", "1.5", "-2.5", ".5", ".25"])

    def test_garbage_fails_loudly(self):
        with self.assertRaises(ValueError):
            list(stencil._tokens("M1 1 #"))


class PathTest(unittest.TestCase):
    def test_relative_and_absolute_forms_give_the_same_stencil(self):
        self.assertEqual(stencil._path("m1 1l2 0v2h-2z"), stencil._path("M1 1L3 1V3H1Z"))

    def test_coordinates_are_rounded_to_a_tenth(self):
        self.assertEqual(stencil._path("M1.04 1.06L2 2"),
                         '<path><move x="1" y="1.1"/><line x="2" y="2"/></path>')

    def test_negative_zero_is_written_as_zero(self):
        self.assertEqual(stencil._f(-0.04), "0")

    def test_repeated_pairs_after_move_are_lines(self):
        self.assertEqual(stencil._path("M0 0 5 5"), '<path><move x="0" y="0"/><line x="5" y="5"/></path>')

    def test_arc_with_compact_flags(self):
        out = stencil._path("M0 0a2 2 0 012 2")
        self.assertIn('<arc rx="2" ry="2" x-axis-rotation="0" large-arc-flag="0" sweep-flag="1" x="2" y="2"/>', out)

    def test_smooth_curve_reflects_the_previous_control_point(self):
        out = stencil._path("M0 0C1 1 2 1 3 0S5 -1 6 0")
        self.assertIn('<curve x1="4" y1="-1" x2="5" y2="-1" x3="6" y3="0"/>', out)


class SvgTest(unittest.TestCase):
    def test_fill_color_is_written_only_when_it_changes(self):
        xml = stencil.stencil_xml(svg('<path fill="#aaa" d="M0 0L1 1"/>', '<path fill="#aaa" d="M2 2L3 3"/>',
                                      '<path fill="#bbb" d="M4 4L5 5"/>'))
        self.assertEqual(xml.count("<fillcolor"), 2)
        self.assertEqual(xml.count("<fill/>"), 3)

    def test_stroke_with_fill_uses_fillstroke(self):
        xml = stencil.stencil_xml(svg('<path fill="#aaa" stroke="#000" stroke-width="2" d="M0 0L1 1"/>'))
        self.assertIn('<strokecolor color="#000"/><strokewidth width="2"/>', xml)
        self.assertIn("<fillstroke/>", xml)

    def test_size_comes_from_the_view_box(self):
        xml = stencil.stencil_xml(svg('<path d="M0 0L1 1"/>', view_box="0 0 38.5 42"))
        self.assertTrue(xml.startswith('<shape w="38.5" h="42" aspect="fixed">'))

    def test_unsupported_things_raise_instead_of_drawing_something_else(self):
        cases = {
            "transform": svg('<path transform="rotate(5)" d="M0 0L1 1"/>'),
            "fill-rule": svg('<path fill-rule="evenodd" d="M0 0L1 1"/>'),
            "rect": svg('<rect width="1" height="1"/>'),
            "circle": svg('<circle r="1"/>'),
        }
        for name, source in cases.items():
            with self.subTest(name):
                with self.assertRaises(ValueError):
                    stencil.stencil_xml(source)

    def test_compression_round_trips(self):
        xml = stencil.stencil_xml(svg('<path d="M0 0L1 1"/>'))
        self.assertEqual(decode(stencil.compress(xml)), xml)

    def test_a_catalog_stencil_decodes_to_a_shape(self):
        style = load_catalog()["icons"][0]["style"]
        payload = style.split("shape=stencil(")[1].split(")")[0]
        self.assertTrue(decode(payload).startswith("<shape "))


if __name__ == "__main__":
    unittest.main()
