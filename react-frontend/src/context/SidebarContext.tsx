"use client"

import React, { createContext, useContext, useState, useEffect } from "react"

type SidebarContextType = {
  isOpen: boolean
  toggle: () => void
  setOpen: (v: boolean) => void
}

const SidebarContext = createContext<SidebarContextType | undefined>(undefined)

export function SidebarProvider({ children }: { children: React.ReactNode }) {
  const [isOpen, setIsOpen] = useState(true)

  // restore persisted state
  useEffect(() => {
    const saved = localStorage.getItem("sidebar-open")
    if (saved !== null) setIsOpen(saved === "true")
  }, [])

  // persist state
  useEffect(() => {
    localStorage.setItem("sidebar-open", String(isOpen))
  }, [isOpen])

  const toggle = () => setIsOpen((v) => !v)

  return (
    <SidebarContext.Provider value={{ isOpen, toggle, setOpen: setIsOpen }}>
      {children}
    </SidebarContext.Provider>
  )
}

export function useSidebar() {
  const ctx = useContext(SidebarContext)
  if (!ctx) throw new Error("useSidebar must be used within SidebarProvider")
  return ctx
}
