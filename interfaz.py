import customtkinter as ctk

# título, artista, tempo (BPM), energía, bailabilidad
CANCIONES = (
    ("Luz de mañana", "Mar Abierto", 92, 0.48, 0.64),
    ("Ciudad de noche", "Norte", 124, 0.86, 0.81),
    ("Después de la lluvia", "Luna Azul", 76, 0.32, 0.45),
)

class AnalisisMusical(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Análisis musical")
        self.geometry("600x840")
        self.minsize(400, 480)
        self.seleccion = ctk.IntVar(self, value=-1)
        self.negrita = ctk.CTkFont(size=14, weight="bold")

        ctk.CTkLabel(self, text="Análisis musical",
                     font=ctk.CTkFont(size=26, weight="bold")).pack(pady=(20, 10))
        ctk.CTkLabel(self, text="Biblioteca de ejemplo", text_color="gray").pack()
        self.busqueda = ctk.CTkEntry(self, placeholder_text="Título o artista")
        self.busqueda.pack(fill="x", padx=40, pady=10)
        self.busqueda.bind("<Return>", lambda _: self.filtrar())
        ctk.CTkButton(self, text="Buscar", height=40, font=self.negrita,
                      command=self.filtrar).pack(pady=10)
        ctk.CTkLabel(self, text="Canciones", font=self.negrita).pack(anchor="w", padx=40)
        self.lista = ctk.CTkScrollableFrame(self)
        self.lista.pack(fill="both", expand=True, padx=40, pady=5)
        self.detalle = ctk.CTkLabel(self, text="", justify="left")
        self.detalle.pack(pady=15)
        self.filtrar()

    def filtrar(self):
        consulta = self.busqueda.get().strip().casefold()
        for fila in self.lista.winfo_children():
            fila.destroy()
        self.seleccion.set(-1)
        hay_resultados = False
        for indice, (titulo, artista, *_) in enumerate(CANCIONES):
            if consulta in f"{titulo} {artista}".casefold():
                hay_resultados = True
                ctk.CTkRadioButton(
                    self.lista, text=f"{titulo} · {artista}", value=indice,
                    variable=self.seleccion, command=self.mostrar_detalle,
                ).pack(anchor="w", padx=10, pady=8)
        self.detalle.configure(text="Selecciona una canción para ver sus características."
                               if hay_resultados else "No se encontraron canciones.")

    def mostrar_detalle(self):
        titulo, artista, tempo, energia, baile = CANCIONES[self.seleccion.get()]
        self.detalle.configure(text=f"{titulo} · {artista}\nTempo: {tempo} BPM\n"
                                    f"Energía: {energia:.0%} · Bailabilidad: {baile:.0%}")

if __name__ == "__main__":
    ctk.set_appearance_mode("System")
    ctk.set_default_color_theme("blue")
    AnalisisMusical().mainloop()
