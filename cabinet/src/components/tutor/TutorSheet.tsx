import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import Mascot from "../Mascot";
import ChatBubble from "./ChatBubble";
import {
  quickReplies,
  cannedReplies,
  greeting,
  type TutorMessage,
  type QuickReply,
} from "../../mock/tutor";

interface Props {
  open: boolean;
  onClose: () => void;
}

type Snap = "half" | "full";

// AI-тьютор: bottom sheet (half → full), который НЕ перекрывает активную ступень
// в half-режиме. Мок-чат с сократическими заготовками.
export default function TutorSheet({ open, onClose }: Props) {
  const [snap, setSnap] = useState<Snap>("half");
  const [messages, setMessages] = useState<TutorMessage[]>([greeting]);

  const send = (chip: QuickReply) => {
    const studentMsg: TutorMessage = {
      id: `s-${Date.now()}`,
      from: "student",
      text: chip,
    };
    const tutorMsg: TutorMessage = {
      id: `t-${Date.now()}`,
      from: "tutor",
      text: cannedReplies[chip],
    };
    setMessages((prev) => [...prev, studentMsg, tutorMsg]);
  };

  const heightClass = snap === "full" ? "h-[88dvh]" : "h-[52dvh]";

  return (
    <AnimatePresence>
      {open && (
        <>
          {/* затемнение — тап закрывает */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
            className="fixed inset-0 z-40 bg-ink/20 backdrop-blur-[2px]"
          />
          <motion.div
            initial={{ y: "100%" }}
            animate={{ y: 0 }}
            exit={{ y: "100%" }}
            transition={{ type: "spring", damping: 30, stiffness: 300 }}
            className={`fixed inset-x-0 bottom-0 z-50 mx-auto flex w-full max-w-[480px] flex-col rounded-t-[24px] bg-card shadow-[var(--shadow-overlay)] ${heightClass}`}
            role="dialog"
            aria-label="Помощник по математике"
          >
            {/* ручка + переключатель размера */}
            <button
              type="button"
              onClick={() => setSnap((s) => (s === "half" ? "full" : "half"))}
              aria-label="Развернуть помощника"
              className="mx-auto mt-2.5 h-1.5 w-12 rounded-pill bg-line focus-visible:outline-none"
            />

            <header className="flex items-center gap-3 px-5 pb-3 pt-2">
              <Mascot size={42} mood="cheer" />
              <div className="min-w-0 flex-1">
                <p className="font-display text-[16px] font-bold text-ink">
                  Помощник
                </p>
                <p className="text-[12px] text-ink-soft">
                  Помогу разобраться сам(а), а не просто дам ответ 😊
                </p>
              </div>
              <button
                type="button"
                onClick={onClose}
                aria-label="Закрыть"
                className="grid h-9 w-9 place-items-center rounded-pill bg-paper text-ink-soft ring-1 ring-line hover:bg-line/40 focus-visible:outline-none"
              >
                ✕
              </button>
            </header>

            {/* лента сообщений */}
            <div className="flex-1 space-y-2.5 overflow-y-auto px-5 py-2">
              {messages.map((m) => (
                <ChatBubble key={m.id} msg={m} />
              ))}
            </div>

            {/* чипы быстрых ответов + safe-area */}
            <div
              className="border-t border-line bg-card px-4 pt-3"
              style={{ paddingBottom: "max(env(safe-area-inset-bottom), 12px)" }}
            >
              <div className="flex flex-wrap gap-2">
                {quickReplies.map((chip) => (
                  <button
                    key={chip}
                    type="button"
                    onClick={() => send(chip)}
                    className="rounded-pill bg-paper px-3.5 py-2 text-[13px] font-medium text-ink-soft ring-1 ring-line transition hover:bg-brand-wash hover:text-brand-deep active:scale-95 focus-visible:outline-none"
                  >
                    {chip}
                  </button>
                ))}
              </div>
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}
