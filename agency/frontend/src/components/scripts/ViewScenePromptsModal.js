"use client";

import { useState } from "react";
import {
  Film,
  X,
  Copy,
  Check,
  Video,
  Sparkles,
  Camera,
  Layers,
  Clock,
} from "lucide-react";

/**
 * ViewScenePromptsModal
 * Modal interactivo estilo macOS Finder para inspeccionar y copiar los Prompts Cinemáticos
 * de Video IA desglosados por escenas de 5 segundos para generadores (Wan 2.1, Sora, Runway, CogVideoX).
 */
export function ViewScenePromptsModal({
  isOpen,
  onClose,
  script,
  scenes = [],
  loading = false,
  onRenderVideo,
}) {
  const [copiedIndex, setCopiedIndex] = useState(null);

  if (!isOpen || !script) return null;

  const handleCopyPrompt = (text, idx) => {
    navigator.clipboard.writeText(text);
    setCopiedIndex(idx);
    setTimeout(() => setCopiedIndex(null), 2500);
  };

  const scriptTitle = script.gancho_0_5s || script.title || "Guion Viral 9:16";

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-md animate-fade-in">
      <div className="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-3xl shadow-2xl overflow-hidden flex flex-col max-h-[90vh]">
        {/* Cabecera Estilo Ventana macOS (Botones 🔴 🟡 🟢 + Título) */}
        <div className="flex items-center justify-between border-b border-slate-800 px-5 py-3.5 bg-slate-950/80">
          <div className="flex items-center gap-2">
            <span className="w-3 h-3 rounded-full bg-rose-500/80"></span>
            <span className="w-3 h-3 rounded-full bg-amber-500/80"></span>
            <span className="w-3 h-3 rounded-full bg-emerald-500/80"></span>
            <span className="text-xs font-mono font-bold text-indigo-300 ml-2 flex items-center gap-1.5">
              <Film className="w-4 h-4 text-indigo-400" /> Prompts de Video IA por Escenas (~5s)
            </span>
          </div>
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-slate-200 transition-colors p-1 rounded-lg hover:bg-slate-800/60"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Subcabecera con información del Guion */}
        <div className="bg-slate-950/40 border-b border-slate-800/60 p-4 space-y-1">
          <span className="text-[10px] font-mono text-indigo-400 font-bold uppercase tracking-wider block">
            📌 Guion Base:
          </span>
          <h3 className="text-sm font-bold text-slate-100 leading-snug">
            "{scriptTitle}"
          </h3>
          <p className="text-xs text-slate-400">
            Prompts cinemáticos generados por el Agente Director para modelos Text-to-Video / Image-to-Video en formato vertical 9:16.
          </p>
        </div>

        {/* Cuerpo del Modal con el Storyboard de Escenas */}
        <div className="p-5 space-y-4 overflow-y-auto flex-1 custom-scrollbar">
          {loading ? (
            <div className="py-12 text-center space-y-3">
              <Sparkles className="w-8 h-8 text-indigo-400 animate-spin mx-auto" />
              <p className="text-xs text-indigo-300 font-bold font-mono">
                El Agente Director está creando el Storyboard de Prompts IA de 5s...
              </p>
            </div>
          ) : scenes.length === 0 ? (
            <div className="py-8 text-center text-xs text-slate-400">
              No se pudieron generar los prompts. Puedes intentar renderizar el video directamente.
            </div>
          ) : (
            scenes.map((scene, idx) => {
              const isCopied = copiedIndex === idx;
              const timeRange = scene.timestamp_range || `Escena #${idx + 1} (5s)`;
              const blockType = (scene.block_type || "Escena").toUpperCase();
              const cameraShot = scene.camera_shot || "Macro Close-Up / Dynamic Motion";
              const promptText = scene.visual_prompt || "";

              return (
                <div
                  key={idx}
                  className="bg-slate-950/80 border border-slate-800/90 hover:border-indigo-500/50 rounded-xl p-4 space-y-3 transition-all shadow-md group"
                >
                  {/* Encabezado de la Escena */}
                  <div className="flex items-center justify-between border-b border-slate-800/60 pb-2">
                    <div className="flex items-center gap-2">
                      <span className="bg-indigo-950/80 text-indigo-300 border border-indigo-500/40 text-[10px] font-mono font-bold px-2.5 py-0.5 rounded-md flex items-center gap-1">
                        <Clock className="w-3 h-3 text-indigo-400" /> {timeRange}
                      </span>
                      <span className="bg-amber-950/80 text-amber-300 border border-amber-500/40 text-[10px] font-mono font-bold px-2 py-0.5 rounded-md uppercase">
                        {blockType}
                      </span>
                    </div>

                    <span className="text-[10px] font-mono text-slate-400 flex items-center gap-1">
                      <Camera className="w-3 h-3 text-emerald-400" /> {cameraShot}
                    </span>
                  </div>

                  {/* Locución (Español) */}
                  <div className="space-y-1">
                    <span className="text-[10px] font-mono text-slate-400 uppercase font-bold block">
                      🗣️ Locución (Español):
                    </span>
                    <p className="text-xs text-slate-200 bg-slate-900/60 border border-slate-800/60 p-2.5 rounded-lg leading-relaxed italic">
                      "{scene.audio_text}"
                    </p>
                  </div>

                  {/* Prompt Cinemático (Inglés) */}
                  <div className="space-y-1">
                    <div className="flex items-center justify-between">
                      <span className="text-[10px] font-mono text-indigo-400 uppercase font-bold block">
                        🎬 Prompt Visual Cinemático para IA (English 9:16):
                      </span>
                      <button
                        onClick={() => handleCopyPrompt(promptText, idx)}
                        className={`text-[10px] font-bold px-2.5 py-1 rounded-md flex items-center gap-1 transition-all ${
                          isCopied
                            ? "bg-emerald-600 text-white"
                            : "bg-indigo-950 hover:bg-indigo-900 text-indigo-300 border border-indigo-500/40"
                        }`}
                      >
                        {isCopied ? (
                          <>
                            <Check className="w-3 h-3" /> ¡Prompt Copiado!
                          </>
                        ) : (
                          <>
                            <Copy className="w-3 h-3" /> Copiar Prompt
                          </>
                        )}
                      </button>
                    </div>

                    <div className="bg-slate-900 border border-indigo-500/30 p-3 rounded-lg text-xs font-mono text-indigo-200 leading-relaxed select-all">
                      {promptText}
                    </div>
                  </div>
                </div>
              );
            })
          )}
        </div>

        {/* Pie de Página del Modal */}
        <div className="border-t border-slate-800 p-4 bg-slate-950/80 flex items-center justify-between">
          <button
            onClick={onClose}
            className="px-4 py-2 bg-slate-900 hover:bg-slate-800 text-slate-300 border border-slate-700 rounded-xl text-xs font-bold transition-colors"
          >
            Cerrar
          </button>

          {onRenderVideo && (
            <button
              onClick={() => {
                onClose();
                onRenderVideo(script);
              }}
              className="bg-indigo-600 hover:bg-indigo-500 text-white font-bold text-xs px-4 py-2 rounded-xl shadow-lg flex items-center gap-2 transition-all"
            >
              <Video className="w-4 h-4" /> Renderizar Video con estas Escenas →
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
