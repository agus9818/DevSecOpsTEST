# Usa una imagen base oficial de Python
FROM python:3.14

# Establece el directorio de trabajo dentro del contenedor
WORKDIR /app

# Copia los archivos de dependencia e instala
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# COPIAR SOLO EL CÓDIGO NECESARIO
# Copia tu aplicación Flask
COPY app.py .

# Exponer el puerto
EXPOSE 5000

ENTRYPOINT ["python", "-m", "flask"]
# Comando para ejecutar la aplicación
# Usamos 0.0.0.0 aquí porque está dentro de un entorno Docker aislado.
CMD ["python", "app.py"]