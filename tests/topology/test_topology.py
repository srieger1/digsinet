import unittest
from topology import TopologyBuilder


class TopologyTests(unittest.TestCase):

    def setUp(self):
        self.b = TopologyBuilder()

    def test_topology_builder(self):
        self.b = TopologyBuilder()
        self.b.add_node("srl1", "nokia_srlinux")
        self.b.add_node("srl2", "nokia_srlinux")
        self.b.add_link("srl1", "srl2", "e1-1", "e1-1")

        topo = self.b.build()
        self.assertEqual(len(topo.nodes), 2)
        self.assertEqual(len(topo.links), 1)

        self.assertEqual(topo.nodes[0].name, "srl1")
        self.assertEqual(topo.nodes[1].name, "srl2")
        self.assertEqual(topo.links[0].name_from, "srl1")
        self.assertEqual(topo.links[0].name_to, "srl2")
        self.assertEqual(topo.links[0].interface_to, "e1-1")
        self.assertEqual(topo.links[0].interface_from, "e1-1")

    def test_topology_faulty_link(self):
        self.b.add_node("srl1", "nokia_srlinux")
        with self.assertRaises(AssertionError):
            self.b.add_link("srl1", "srl2", "e1-1", "e1-1")

    def test_topology_clear(self):
        self.b.add_node("srl1", "nokia_srlinux")
        self.b.add_node("srl2", "nokia_srlinux")
        self.b.add_link("srl1", "srl2", "e1-1", "e1-1")
        self.b.clear()
        topo = self.b.build()

        self.assertEqual(len(topo.nodes), 0)
        self.assertEqual(len(topo.links), 0)
