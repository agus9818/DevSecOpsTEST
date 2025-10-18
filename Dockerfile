# 1. Usa una imagen base 'slim' y una versión de Python estable.
# Esto reduce el tamaño de la imagen y la superficie de ataque.
FROM python:3.12-slim

# Establece el directorio de trabajo dentro del contenedor
WORKDIR /app

# 2. Crea un usuario sin privilegios para ejecutar la aplicación.
RUN useradd --create-home appuser

# Copia los archivos de dependencia e instala
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia el código de la aplicación y establece la propiedad al nuevo usuario
COPY app.py .
RUN chown -R appuser:appuser /app

# Cambia al usuario sin privilegios
USER appuser

# Expone el puerto (documentación)
EXPOSE 5000

# 3. Comando de inicio corregido.
# Ejecuta la aplicación directamente, ya que app.py tiene el bloque if __name__ == '__main__':
CMD ["python", "app.py"]