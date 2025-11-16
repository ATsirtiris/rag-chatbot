"use client";

import { useState } from "react";



type Toast = { id: number; text: string };

export function useToast() {

const [toasts, setToasts] = useState<Toast[]>([]);

function push(text: string) {

const id = Date.now();

setToasts((t) => [...t, { id, text }]);

setTimeout(() => setToasts((t) => t.filter((x) => x.id !== id)), 3500);

}

const node = (

<div className="fixed top-3 right-3 space-y-2 z-50">

{toasts.map((t) => (

<div key={t.id} className="rounded-xl bg-neutral-900 text-white px-3 py-2 shadow-lg">

{t.text}

</div>

))}

</div>

);

return { push, node } as const;

}

