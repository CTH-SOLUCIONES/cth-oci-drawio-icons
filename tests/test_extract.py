"""extract.py: input handling, the segmentation of the Icons page and the slug rule.

The extraction itself (draw.io export, SVGO) is not run here: it needs the desktop app and Oracle's toolkit.
"""
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock
import xml.etree.ElementTree as ET

from support import run_main  # first: puts scripts/ on sys.path

import extract  # noqa: E402


def vertex(cell_id, x, y, w, h, value="", style="rounded=0;fillColor=#fff;strokeColor=#000;", parent="1"):
    return (f'<mxCell id="{cell_id}" value="{value}" style="{style}" vertex="1" parent="{parent}">'
            f'<mxGeometry x="{x}" y="{y}" width="{w}" height="{h}" as="geometry"/></mxCell>')


def page(*cells):
    return ET.fromstring('<mxGraphModel><root><mxCell id="0"/><mxCell id="1" parent="0"/>' + "".join(cells)
                         + "</root></mxGraphModel>")


class InputHandlingTest(unittest.TestCase):
    def test_no_toolkit_given_fails_with_a_clear_message(self):
        with mock.patch.dict(os.environ, clear=False):
            os.environ.pop("OCI_TOOLKIT", None)
            _, _, code = run_main(lambda a: extract.toolkit_path(a), [])
        self.assertIn("OCI_TOOLKIT", code)

    def test_missing_file_is_named_in_the_message(self):
        with mock.patch.dict(os.environ, {"OCI_TOOLKIT": "/nonexistent/toolkit.drawio"}):
            _, _, code = run_main(lambda a: extract.toolkit_path(a), [])
        self.assertIn("/nonexistent/toolkit.drawio", code)

    def test_env_variable_and_argument_both_work_and_the_argument_wins(self):
        with tempfile.TemporaryDirectory() as tmp:
            from_env, from_arg = Path(tmp) / "env.drawio", Path(tmp) / "arg.drawio"
            from_env.write_text("<mxfile/>")
            from_arg.write_text("<mxfile/>")
            with mock.patch.dict(os.environ, {"OCI_TOOLKIT": str(from_env)}):
                self.assertEqual(extract.toolkit_path([]), from_env)
                self.assertEqual(extract.toolkit_path([str(from_arg)]), from_arg)

    def test_no_personal_default_path_is_left_in_the_source(self):
        source = Path(extract.__file__).read_text(encoding="utf-8")
        self.assertNotIn("/Volumes/", source)
        self.assertNotIn("/Users/", source)

    def test_drawio_binary_comes_from_the_environment_and_must_exist(self):
        with mock.patch.dict(os.environ, {"DRAWIO_BIN": "/nonexistent/draw.io"}):
            _, _, code = run_main(lambda a: extract.drawio_binary(), [])
        self.assertIn("DRAWIO_BIN", code)
        with tempfile.NamedTemporaryFile() as fake, mock.patch.dict(os.environ, {"DRAWIO_BIN": fake.name}):
            self.assertEqual(extract.drawio_binary(), fake.name)

    def test_drawio_binary_environment_overrides_the_default(self):
        with tempfile.NamedTemporaryFile() as default, tempfile.NamedTemporaryFile() as from_env:
            with mock.patch.object(extract, "DEFAULT_DRAWIO_BIN", default.name):
                with mock.patch.dict(os.environ, {"DRAWIO_BIN": from_env.name}):
                    self.assertEqual(extract.drawio_binary(), from_env.name)
                with mock.patch.dict(os.environ):
                    os.environ.pop("DRAWIO_BIN", None)
                    self.assertEqual(extract.drawio_binary(), default.name)

    def test_main_stops_before_any_work_when_the_toolkit_is_missing(self):
        with mock.patch.dict(os.environ, clear=False), mock.patch.object(extract.subprocess, "run") as run:
            os.environ.pop("OCI_TOOLKIT", None)
            _, _, code = run_main(extract.main, [])
        self.assertIsInstance(code, str)
        run.assert_not_called()


class VersionTest(unittest.TestCase):
    def test_source_names_the_toolkit_version_and_not_the_repo_revision(self):
        self.assertEqual(extract.SOURCE, "OCI Architecture Diagram Toolkit v24.2 (Oracle): "
                                         "Icons page, and the legend of the Physical page")

    def test_base_url_is_pinned_to_the_release(self):
        self.assertTrue(extract.BASE_URL.endswith(f"@{extract.VERSION}/svg"))


class SlugTest(unittest.TestCase):
    def test_slug_rules(self):
        cases = {"OCI Compute": "compute", "oci Data Science": "data-science", "E-Business Suite": "e-business-suite",
                 "Café  Ñandú": "cafe-nandu", "  Load Balancer (Public) ": "load-balancer-public",
                 "OCIFoo": "ocifoo", "***": ""}
        for label, slug in cases.items():
            with self.subTest(label):
                self.assertEqual(extract.make_slug(label), slug)

    def test_plain_text_strips_markup_and_entities(self):
        self.assertEqual(extract.plain_text("<div>Block&nbsp;<b>Volume</b></div>"), "Block Volume")
        self.assertEqual(extract.plain_text("a &amp;amp; b"), "a & b")
        self.assertEqual(extract.plain_text(None), "")


class SegmentationTest(unittest.TestCase):
    def setUp(self):
        self.root = page(
            vertex("h", 0, 0, 100, 20, value="Compute", style="text;fontStyle=1;"),
            # a pictogram of two touching shapes, label below, 8 px gap
            vertex("a1", 10, 40, 20, 20), vertex("a2", 30, 40, 20, 20),
            vertex("l1", 0, 68, 60, 14, value="OCI Foo", style="text;"),
            # a second pictogram far away, its label split in two lines
            vertex("b1", 200, 40, 40, 40),
            vertex("l2", 190, 84, 60, 14, value="Bar", style="text;"),
            vertex("l3", 190, 98, 60, 14, value="Service", style="text;"),
            # a big frame is not a pictogram part; an invisible shape neither
            vertex("frame", 0, 0, 900, 900, style="rounded=0;fillColor=none;strokeColor=#000;"),
            vertex("ghost", 100, 40, 20, 20, style="fillColor=none;strokeColor=none;"),
        )

    def test_touching_shapes_are_one_pictogram_with_its_label(self):
        icons, _ = extract.segment(self.root)
        by_label = {i["label"]: i for i in icons}
        self.assertEqual(set(by_label), {"OCI Foo", "Bar Service"})
        foo = by_label["OCI Foo"]
        self.assertEqual((foo["x"], foo["y"], foo["w"], foo["h"]), (10, 40, 40, 20))
        self.assertEqual({p["id"] for p in foo["parts"]}, {"a1", "a2"})

    def test_a_split_label_is_joined_top_to_bottom(self):
        icons, _ = extract.segment(self.root)
        self.assertIn("Bar Service", [i["label"] for i in icons])

    def test_category_is_the_closest_heading_above_and_labels_are_not_headings(self):
        icons, texts = extract.segment(self.root)
        extract.assign_categories(icons, texts)
        self.assertEqual({i["label"]: i["category"] for i in icons}, {"OCI Foo": "Compute", "Bar Service": "Compute"})

    def test_a_pictogram_with_no_heading_above_is_other(self):
        root = page(vertex("a", 0, 100, 20, 20), vertex("l", -10, 124, 40, 14, value="Solo", style="text;"))
        icons, texts = extract.segment(root)
        extract.assign_categories(icons, texts)
        self.assertEqual(icons[0]["category"], "Other")

    def test_a_label_further_than_the_gap_is_not_attached(self):
        root = page(vertex("a", 0, 0, 20, 20), vertex("l", 0, 20 + extract.LABEL_MAX_GAP + 1, 20, 14,
                                                       value="Far", style="text;"))
        icons, _ = extract.segment(root)
        self.assertEqual(icons[0]["label"], "")

    def test_shapes_inside_a_parent_use_absolute_coordinates(self):
        root = page(vertex("p", 100, 200, 10, 10, style="group;"),
                    vertex("c", 5, 6, 20, 20, parent="p"))
        shapes = extract.shapes_of(root)
        self.assertEqual([(s["id"], s["x"], s["y"]) for s in shapes], [("c", 105.0, 206.0)])

    def test_user_object_wrappers_are_resolved(self):
        root = ET.fromstring(
            '<mxGraphModel><root><mxCell id="0"/><mxCell id="1" parent="0"/>'
            '<object label="Wrapped" id="w"><mxCell style="text;" vertex="1" parent="1">'
            '<mxGeometry x="1" y="2" width="3" height="4" as="geometry"/></mxCell></object></root></mxGraphModel>')
        shapes = extract.shapes_of(root)
        self.assertEqual([(s["id"], s["text"]) for s in shapes], [("w", "Wrapped")])

    def test_drawio_of_places_parts_at_the_origin(self):
        icons, _ = extract.segment(self.root)
        foo = next(i for i in icons if i["label"] == "OCI Foo")
        xml = extract.drawio_of(foo)
        ET.fromstring(xml)  # well-formed
        self.assertIn('x="0.000" y="0.000" width="20.000" height="20.000"', xml)
        self.assertIn('x="20.000" y="0.000"', xml)


if __name__ == "__main__":
    unittest.main()
