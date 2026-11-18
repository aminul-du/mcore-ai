"use client";
import { useState } from "react";
import { Server, Shield, KeyRound, CheckCircle2, Cloud } from "lucide-react";

export default function InfraControlPlane() {
  const [nodes] = useState([
    { id: "MCORE-L1", type: "Debian VPS", location: "Bangladesh", status: "Healthy", ping: "12ms" },
    { id: "AWS-L2", type: "EC2 T3", location: "ap-south-1", status: "Healthy", ping: "45ms" },
    { id: "GCP-L3", type: "Compute Engine", location: "asia-south1", status: "Healthy", ping: "42ms" }
  ]);

  return (
    <div className="flex flex-col gap-6">
      <div className="grid grid-cols-3 gap-4">
        {nodes.map(node => (
          <div key={node.id} className="bg-[#191f2b] border border-[#303a4c] rounded-xl p-5 relative overflow-hidden">
            <div className="absolute top-0 right-0 p-4">
               <CheckCircle2 className="text-[#34a853] w-5 h-5" />
            </div>
            <Server className="w-8 h-8 text-[#4285f4] mb-3" />
            <h3 className="font-bold text-lg">{node.id}</h3>
            <p className="text-sm text-[#aab5c6]">{node.type} · {node.location}</p>
            <div className="mt-4 flex justify-between text-xs text-[#aab5c6]">
              <span>Matrix Core Telemetry:</span>
              <span className="font-mono">{node.ping}</span>
            </div>
          </div>
        ))}
      </div>

      <div className="bg-[#191f2b] border border-[#303a4c] rounded-xl p-5 mt-4">
        <h3 className="font-bold text-lg mb-4 flex items-center gap-2"><KeyRound className="w-5 h-5"/> SSH Key Inventory & IAM</h3>
        <table className="w-full text-left text-sm">
          <thead>
            <tr className="border-b border-[#303a4c] text-[#aab5c6]">
              <th className="pb-2">Identity</th>
              <th className="pb-2">Algorithm</th>
              <th className="pb-2">Target Node</th>
              <th className="pb-2">Rotation</th>
            </tr>
          </thead>
          <tbody>
            <tr className="border-b border-[#303a4c]">
              <td className="py-3 font-mono">id_ed25519_mcore_new</td>
              <td>Ed25519</td>
              <td>MCORE-L1</td>
              <td className="text-[#34a853]">Verified</td>
            </tr>
            <tr>
              <td className="py-3 font-mono">ec2_key</td>
              <td>RSA-4096</td>
              <td>AWS-L2</td>
              <td className="text-[#fbc02d]">Due 30d</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  );
}
