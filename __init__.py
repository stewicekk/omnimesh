from .reference_agent import ReferenceAgent
from .vision_agent import VisionAgent
from .segmentation_agent import SegmentationAgent
from .geometry_agent import GeometryAgent
from .part_agent import PartAgent
from .material_agent import MaterialAgent
from .texture_agent import TextureAgent
from .topology_agent import TopologyAgent
from .u_v_agent import UVAgent
from .retopo_agent import RetopoAgent
from .rig_agent import RigAgent
from .animation_agent import AnimationAgent
from .l_o_d_agent import LODAgent
from .optimization_agent import OptimizationAgent
from .game_ready_agent import GameReadyAgent
from .critic_agent import CriticAgent
from .repair_agent import RepairAgent
from .license_agent import LicenseAgent
from .resource_agent import ResourceAgent
from .pipeline_agent import PipelineAgent
from .memory_agent import MemoryAgent
from .research_agent import ResearchAgent

AGENT_CLASSES = {
    "reference_agent": ReferenceAgent,
    "vision_agent": VisionAgent,
    "segmentation_agent": SegmentationAgent,
    "geometry_agent": GeometryAgent,
    "part_agent": PartAgent,
    "material_agent": MaterialAgent,
    "texture_agent": TextureAgent,
    "topology_agent": TopologyAgent,
    "u_v_agent": UVAgent,
    "retopo_agent": RetopoAgent,
    "rig_agent": RigAgent,
    "animation_agent": AnimationAgent,
    "l_o_d_agent": LODAgent,
    "optimization_agent": OptimizationAgent,
    "game_ready_agent": GameReadyAgent,
    "critic_agent": CriticAgent,
    "repair_agent": RepairAgent,
    "license_agent": LicenseAgent,
    "resource_agent": ResourceAgent,
    "pipeline_agent": PipelineAgent,
    "memory_agent": MemoryAgent,
    "research_agent": ResearchAgent
}
