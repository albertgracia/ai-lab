export type InfraNode = {
  name: string;
  role: string;
  status: string;
  cpu: string;
  gpu: string;
  ram: string;
  storage: string;
  network: string;
  system: string;
  details: { label: string; value: string }[];
};

export type InfraInventory = {
  generated_at: string;
  visibility: string;
  summary: {
    physical_nodes: number;
    gpu_workstations: number;
    nas_hyperv_nodes: number;
    network: string;
    wifi: string;
    cabling: string;
  };
  nodes: InfraNode[];
  network: {
    cabling: string;
    longest_run: string;
    gateway: {
      name: string;
      uplink: string;
      handoff: string;
      trunk: string;
    };
    switch: {
      name: string;
      port: string;
      uplink: string;
    };
    aps: {
      name: string;
      port: string;
    }[];
  };
  capabilities: string[];
  pending: string[];
  security: {
    excluded: string[];
    notes: string[];
  };
  source: string;
};

export const infraInventory: InfraInventory = {
  generated_at: "2026-05-31",
  visibility: "sanitized-public",
  source: "Operator-provided physical infrastructure inventory",
  summary: {
    physical_nodes: 3,
    gpu_workstations: 2,
    nas_hyperv_nodes: 1,
    network: "UniFi multi-gigabit (10 Gb / 2.5 Gb)",
    wifi: "Wi-Fi 7",
    cabling: "CAT6B",
  },
  nodes: [
    {
      name: "NAS-N5 / Minisforum N5",
      role: "NAS + Hyper-V host",
      status: "operational",
      cpu: "AMD Ryzen 7 255 (8C / 16T, up to 4.9 GHz)",
      gpu: "AMD Radeon 780M iGPU",
      ram: "64 GB DDR5-5600 (2×32 GB, no ECC)",
      storage: "Installed: 1 TB NVMe PCIe 4.0 + 1 TB NVMe via Silverstone PCIe x4 adapter + 4 TB SATA; support: 5 SATA bays + NVMe/U.2 PCIe 4.0 slots",
      network: "10 GbE RJ45 + 5 GbE RJ45",
      system: "Windows 11 Pro + Hyper-V (Ubuntu Server 26.04 / Windows Server 2025 VMs)",
      details: [
        { label: "Platform ceiling", value: "Up to 96 GB RAM" },
        { label: "Connectivity", value: "HDMI 2.1, USB4, OCuLink, PCIe x16 physical / PCIe 4.0 x4" },
        { label: "Power", value: "19 V / 14.73 A / 280 W" },
        { label: "Installed storage", value: "1 TB NVMe + 1 TB NVMe (adapter) + 4 TB SATA" },
      ],
    },
    {
      name: "GPU Workstation A",
      role: "Heavy GPU workstation",
      status: "operational",
      cpu: "AMD Ryzen 7 7800X3D",
      gpu: "PowerColor Red Devil AMD Radeon RX 9070 OC 16 GB GDDR6 (BIOS 9070XT)",
      ram: "64 GB DDR5-6000 (2×32 GB, CL30)",
      storage: "1 TB NVMe PCIe 4.0 + 2 TB NVMe PCIe 4.0 + 2 TB NVMe PCIe 4.0 + 1 TB NVMe PCIe 3.0 + 4 TB SATA",
      network: "No documentado en la fuente",
      system: "Workstation GPU para carga pesada / laboratorio local",
      details: [
        { label: "Case + PSU", value: "Havn HS 420 VGPU blanca + Lian Li Edge EG1300 1300 W ATX 3.1" },
        { label: "Motherboard", value: "Gigabyte X870E AORUS PRO Ice WiFi 7" },
        { label: "Cooling", value: "EKWB FLT 360 DDC + P360M (blanco) + Velocity 2 AM5 (blanco)" },
        { label: "Fans", value: "5× Lian Li Uni Fan AL 140 V2 + 6× Lian Li Uni Fan AL 120 V2" },
      ],
    },
    {
      name: "GPU Workstation B",
      role: "Secondary GPU workstation",
      status: "operational",
      cpu: "AMD Ryzen 5 9600X",
      gpu: "XFX Mercury 310 AMD Radeon RX 7900 XT 20 GB",
      ram: "64 GB DDR5-6000 (2×32 GB, CL30)",
      storage: "1 TB NVMe PCIe 4.0 + 256 GB NVMe PCIe 4.0 + 2 TB SATA",
      network: "No documentado en la fuente",
      system: "Workstation GPU secundaria / laboratorio local",
      details: [
        { label: "PSU + board", value: "Gigabyte 1000 W + Gigabyte X870 AORUS Elite WiFi 7 Ice (Rev 1.1)" },
        { label: "Cooling", value: "EKWB FLT 240 DDC + P360M (negro) + Velocity 2 AM5 (negro)" },
        { label: "Fans", value: "3× CoolerMaster Mobius ARGB 140 mm + 7× CoolerMaster Mobius ARGB 120 mm" },
        { label: "Notes", value: "Plataforma lista para cargas GPU locales y expansión de scheduler multi-GPU" },
      ],
    },
  ],
  network: {
    cabling: "CAT6B",
    longest_run: "25 m",
    gateway: {
      name: "UCG Fiber / Cloud Gateway Fiber",
      uplink: "Telefónica España 1 GbE",
      handoff: "SFP GPON Telefónica",
      trunk: "SFP+ 10 Gb hacia USW Flex 2.5G 8 PoE",
    },
    switch: {
      name: "USW Flex 2.5G 8 PoE",
      port: "Puerto 6",
      uplink: "SFP+ 10 Gb hacia el gateway",
    },
    aps: [
      { name: "U7 In-Wall", port: "3" },
      { name: "U7 Lite", port: "7" },
    ],
  },
  capabilities: [
    "Virtualización Hyper-V en el nodo NAS",
    "Laboratorio GPU local para cargas de IA y render",
    "Red UniFi multi-gigabit con Wi-Fi 7",
    "Base de observabilidad y documentación operativa",
    "Cimientos para scheduler multi-GPU futuro",
  ],
  pending: [
    "Formalizar roles exactos por nodo en el roadmap",
    "Mapear VMs y cargas por host",
    "Completar inventario de IPs/servicios si se decide exponerlo internamente",
    "Vincular la página al roadmap de forma explícita",
    "Definir la acción operativa de Hyper-V checkpoint",
    "Diseñar el scheduler multi-GPU del runtime",
  ],
  security: {
    excluded: [
      "Identificador completo del SFP/ONT GPON",
      "Seriales de hardware",
      "Credenciales o tokens",
      "Códigos exactos de módulos ópticos",
    ],
    notes: [
      "La página se publica con inventario sanitizado para evitar exponer datos sensibles innecesarios.",
      "Se conserva la topología útil (nodos, red y capacidades) sin publicar identificadores ópticos completos.",
    ],
  },
};
