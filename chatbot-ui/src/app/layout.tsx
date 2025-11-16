import type { Metadata } from "next";

import "./globals.css";



export const metadata: Metadata = {

title: "MSc Chatbot",

description: "Next.js UI for FastAPI chatbot",

};



export default function RootLayout({ children }: { children: React.ReactNode }) {

return (

<html lang="en">

<body>{children}</body>

</html>

);

}
