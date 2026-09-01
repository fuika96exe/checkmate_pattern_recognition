import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "象棋開局辨認實驗室",
  description: "以棋形及 RecognitionState 測試中國象棋開局辨認規則。",
  icons: { icon: "/favicon.svg", shortcut: "/favicon.svg" },
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="zh-Hant"><body>{children}</body></html>;
}
