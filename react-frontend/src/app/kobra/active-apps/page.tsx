"use client";

import React, { useState, useEffect } from "react";
import { toast } from "sonner";
import {
  flexRender,
  getCoreRowModel,
  useReactTable,
  ColumnDef,
  getPaginationRowModel,
} from "@tanstack/react-table";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  PlusCircle,
  Loader2,
  Check,
  X,
  ChevronLeft,
  ChevronRight,
  ChevronsLeft,
  ChevronsRight,
} from "lucide-react";

interface Application {
  id: string | number;
  name: string;
  slug: string;
  base_model_name: string;
  created_at: string;
  description?: string;
  [key: string]: any;
}

export default function ApplicationsPage() {
  const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL;
  const token = typeof window !== "undefined" ? localStorage.getItem("access_token") : null;

  const [apps, setApps] = useState<Application[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isOpen, setIsOpen] = useState(false);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [selectedRow, setSelectedRow] = useState<Application | null>(null);
  const [editMode, setEditMode] = useState(false);
  const [formData, setFormData] = useState({ name: "", slug: "", description: "" });

  const [refreshFlag, setRefreshFlag] = useState(false);

  // Fetch apps
  useEffect(() => {
    async function fetchApps() {
      try {
        setLoading(true);
        setError(null);
        const res = await fetch(`${API_BASE_URL}/guardrails/apps/`, {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (!res.ok) {
          toast.error("Failed to fetch applications");
          throw new Error("Failed to fetch applications");
        }
        const data = await res.json();
        setApps(data?.applications || data || []);
      } catch (err: any) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    }
    fetchApps();
  }, [refreshFlag]);

  // Handle new app form
  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) =>
    setFormData({ ...formData, [e.target.name]: e.target.value });

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);

    try {
      if (!token) throw new Error("Unauthorized: Missing token");

      const res = await fetch(`${API_BASE_URL}/guardrails/apps/`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify(formData),
      });

      if (!res.ok) throw new Error("Failed to create application");

      toast.success("New application added successfully!");
      setFormData({ name: "", slug: "", description: "" });
      setIsOpen(false);
      setRefreshFlag((prev) => !prev);
    } catch (error: any) {
      console.error(error);
      toast.error(error.message || "Error adding application");
    } finally {
      setLoading(false);
    }
  };

  // Columns definition
  const columns: ColumnDef<Application>[] = [
    {
      header: "Sr. No.",
      accessorFn: (_row, index) => index + 1,
      cell: ({ getValue }) => (
        <div className="text-center text-muted-foreground">{getValue<number>()}</div>
      ),
      size: 80,
    },
    {
      accessorKey: "name",
      header: "Application Name",
      cell: ({ row }) => <span className="font-medium">{row.original.name}</span>,
      size: 300,
    },
    {
      accessorKey: "slug",
      header: "Application Slug",
      cell: ({ row }) => (
        <span className="text-muted-foreground font-mono text-sm">{row.original.slug}</span>
      ),
      size: 250,
    },
    {
      accessorKey: "base_model_name",
      header: "Base Model",
      cell: ({ row }) => (
        <span className="text-muted-foreground font-mono text-sm">
          {row.original.base_model_name}
        </span>
      ),
      size: 250,
    },
    {
      accessorKey: "created_at",
      header: "Date & Time",
      cell: ({ row }) => (
        <div className="text-center">
          {new Date(row.original.created_at).toLocaleString("en-IN", {
            day: "2-digit",
            month: "short",
            year: "numeric",
            hour: "2-digit",
            minute: "2-digit",
          })}
        </div>
      ),
    },
  ];

  // Table setup
  const table = useReactTable({
    data: apps,
    columns,
    getCoreRowModel: getCoreRowModel(),
    getPaginationRowModel: getPaginationRowModel(),
    initialState: { pagination: { pageSize: 10 } },
  });

  // Dialog Save
  const handleSave = async () => {
    if (!selectedRow) return;
    try {
      const res = await fetch(`${API_BASE_URL}/guardrails/apps/${selectedRow.slug}/`, {
        method: "PATCH",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          name: formData.name,
          description: formData.description,
        }),
      });

      if (!res.ok) throw new Error("Failed to update app details");

      const updated = await res.json();
      setSelectedRow(updated);
      setEditMode(false);
      setRefreshFlag((p) => !p);

      toast.success("Application details updated successfully!");
      setDialogOpen(false);
    } catch (err: any) {
      console.error(err);
      toast.error("Error updating application details");
    }
  };

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-semibold tracking-tight mb-1">Active Apps</h1>

        <div className="flex items-center justify-between">
          <p className="text-muted-foreground">
            Manage all LLM-integrated applications connected to Kobra Guardrails.
          </p>

          <Button
            onClick={() => setIsOpen(true)}
            className="bg-indigo-600 hover:bg-indigo-700 text-white"
          >
            <PlusCircle className="mr-2 h-4 w-4" />
            Add Active App
          </Button>
        </div>
      </div>

      {/* Table Section */}
      <div className="rounded-md border border-border/50 bg-background shadow-sm">
        {loading ? (
          <div className="flex justify-center items-center h-48 text-muted-foreground">
            <Loader2 className="animate-spin mr-2" /> Loading applications...
          </div>
        ) : error ? (
          <div className="text-center text-red-500 py-6">{error}</div>
        ) : (
          <>
            <Table>
              <TableHeader className="bg-muted/50">
                {table.getHeaderGroups().map((hg) => (
                  <TableRow key={hg.id}>
                    {hg.headers.map((header) => (
                      <TableHead
                        key={header.id}
                        className={`font-semibold ${
                          header.column.id === "created_at" || header.index === 0
                            ? "text-center"
                            : "text-left"
                        }`}
                      >
                        {flexRender(header.column.columnDef.header, header.getContext())}
                      </TableHead>
                    ))}
                  </TableRow>
                ))}
              </TableHeader>
              <TableBody>
                {table.getRowModel().rows.length ? (
                  table.getRowModel().rows.map((row) => (
                    <TableRow
                      key={row.id}
                      onClick={() => {
                        setSelectedRow(row.original);
                        setDialogOpen(true);
                        setFormData({
                          name: row.original.name,
                          slug: row.original.slug,
                          description: row.original.description || "",
                        });
                      }}
                      className="cursor-pointer even:bg-muted/30 hover:bg-muted/40 transition-colors"
                    >
                      {row.getVisibleCells().map((cell) => (
                        <TableCell key={cell.id}>
                          {flexRender(cell.column.columnDef.cell, cell.getContext())}
                        </TableCell>
                      ))}
                    </TableRow>
                  ))
                ) : (
                  <TableRow>
                    <TableCell
                      colSpan={columns.length}
                      className="h-24 text-center text-muted-foreground"
                    >
                      No results.
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>

            {/* Pagination */}
            <div className="flex items-center justify-between px-2 py-3 border-t">
              <div className="text-sm text-muted-foreground">
                Showing {table.getState().pagination.pageIndex * table.getState().pagination.pageSize + 1} to{" "}
                {Math.min(
                  (table.getState().pagination.pageIndex + 1) * table.getState().pagination.pageSize,
                  table.getFilteredRowModel().rows.length
                )}{" "}
                of {table.getFilteredRowModel().rows.length} entries
              </div>

              <div className="flex items-center space-x-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => table.setPageIndex(0)}
                  disabled={!table.getCanPreviousPage()}
                >
                  <ChevronsLeft className="h-4 w-4" />
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => table.previousPage()}
                  disabled={!table.getCanPreviousPage()}
                >
                  <ChevronLeft className="h-4 w-4" />
                </Button>

                <div className="flex items-center gap-1 text-sm">
                  <span className="text-muted-foreground">Page</span>
                  <span className="font-medium">
                    {table.getState().pagination.pageIndex + 1} of {table.getPageCount()}
                  </span>
                </div>

                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => table.nextPage()}
                  disabled={!table.getCanNextPage()}
                >
                  <ChevronRight className="h-4 w-4" />
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => table.setPageIndex(table.getPageCount() - 1)}
                  disabled={!table.getCanNextPage()}
                >
                  <ChevronsRight className="h-4 w-4" />
                </Button>
              </div>
            </div>
          </>
        )}
      </div>

      {/* Add App Dialog */}
      <Dialog open={isOpen} onOpenChange={setIsOpen}>
        <DialogContent className="sm:max-w-lg">
          <DialogHeader>
            <DialogTitle>Add New Application</DialogTitle>
            <DialogDescription>
              Fill in the details to onboard a new LLM-integrated application.
            </DialogDescription>
          </DialogHeader>

          <form onSubmit={handleSubmit} className="space-y-4 mt-4">
            <div className="space-y-2">
              <Label htmlFor="name">Name</Label>
              <Input id="name" name="name" value={formData.name} onChange={handleChange} required />
            </div>

            <div className="space-y-2">
              <Label htmlFor="slug">Slug</Label>
              <Input id="slug" name="slug" value={formData.slug} onChange={handleChange} required />
            </div>

            <div className="space-y-2">
              <Label htmlFor="description">Description</Label>
              <Input
                id="description"
                name="description"
                value={formData.description}
                onChange={handleChange}
                required
              />
            </div>

            <div className="flex justify-end pt-4">
              <Button variant="outline" onClick={() => setIsOpen(false)} className="mr-2">
                Cancel
              </Button>
              <Button type="submit" disabled={loading}>
                {loading ? "Adding..." : "Add Application"}
              </Button>
            </div>
          </form>
        </DialogContent>
      </Dialog>

      {/* Details Dialog */}
      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent className="max-w-2xl max-h-[80vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Application Details</DialogTitle>
            <DialogDescription>
              View or update information about this LLM-integrated application.
            </DialogDescription>
          </DialogHeader>

          {selectedRow && (
            <div className="grid gap-4 py-4">
              {Object.entries(selectedRow)
                .filter(([key]) => !["config", "owner"].includes(key))
                .map(([key, value]) => (
                  <div
                    key={key}
                    className="grid grid-cols-3 items-start gap-4 border-b border-border/40 pb-3 last:border-0"
                  >
                    <span className="text-sm font-semibold text-muted-foreground capitalize">
                      {key.replace(/_/g, " ")}
                    </span>

                    <span className="col-span-2 text-sm break-all">
                      {editMode && (key === "name" || key === "description") ? (
                        <Input
                          name={key}
                          value={(formData as any)[key] || ""}
                          onChange={handleChange}
                        />
                      ) : (
                        <>{String(value)}</>
                      )}
                    </span>
                  </div>
                ))}

              <div className="flex justify-end gap-3 pt-3">
                {!editMode ? (
                  <Button
                    className="bg-purple-600 hover:bg-purple-700 text-white"
                    onClick={() => setEditMode(true)}
                  >
                    Update Details
                  </Button>
                ) : (
                  <>
                    <Button
                      className="bg-green-600 hover:bg-green-700 text-white"
                      onClick={handleSave}
                    >
                      <Check className="w-4 h-4 mr-1" /> Save
                    </Button>
                    <Button
                      className="bg-red-600 hover:bg-red-700 text-white"
                      onClick={() => setEditMode(false)}
                    >
                      <X className="w-4 h-4 mr-1" /> Cancel
                    </Button>
                  </>
                )}
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}