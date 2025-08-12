package com.example.gymcamera

import android.Manifest
import android.content.ContentValues
import android.content.pm.PackageManager
import android.os.Build
import android.os.Bundle
import android.os.Environment
import android.provider.MediaStore
import android.widget.Toast
import androidx.activity.result.contract.ActivityResultContracts
import androidx.appcompat.app.AppCompatActivity
import androidx.camera.core.CameraSelector
import androidx.camera.core.ImageCapture
import androidx.camera.core.ImageCaptureException
import androidx.camera.core.Preview
import androidx.camera.lifecycle.ProcessCameraProvider
import androidx.core.content.ContextCompat
import androidx.core.net.toUri
import com.example.gymcamera.databinding.ActivityMainBinding
import java.io.File
import java.text.SimpleDateFormat
import java.util.Locale
import java.util.concurrent.Executors

class MainActivity : AppCompatActivity() {

    private lateinit var binding: ActivityMainBinding
    private var imageCapture: ImageCapture? = null

    private val permissionRequester =
        registerForActivityResult(ActivityResultContracts.RequestMultiplePermissions()) { r ->
            val cam = r[Manifest.permission.CAMERA] == true
            val writeOk = if (Build.VERSION.SDK_INT <= 28)
                r[Manifest.permission.WRITE_EXTERNAL_STORAGE] == true else true
            if (cam && writeOk) startCamera() else {
                Toast.makeText(this, "Required permissions not granted", Toast.LENGTH_LONG).show()
                finish()
            }
        }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityMainBinding.inflate(layoutInflater)
        setContentView(binding.root)

        requestNeededPermissions()
        binding.captureButton.setOnClickListener { takePhoto() }
    }

    private fun requestNeededPermissions() {
        val needed = mutableListOf(Manifest.permission.CAMERA)
        if (Build.VERSION.SDK_INT <= 28) needed += Manifest.permission.WRITE_EXTERNAL_STORAGE
        val missing = needed.filter {
            ContextCompat.checkSelfPermission(this, it) != PackageManager.PERMISSION_GRANTED
        }
        if (missing.isEmpty()) startCamera() else permissionRequester.launch(missing.toTypedArray())
    }

    private fun startCamera() {
        val cameraProviderFuture = ProcessCameraProvider.getInstance(this)
        cameraProviderFuture.addListener({
            val provider = cameraProviderFuture.get()
            val preview = Preview.Builder().build().also {
                it.setSurfaceProvider(binding.viewFinder.surfaceProvider)
            }
            imageCapture = ImageCapture.Builder()
                .setCaptureMode(ImageCapture.CAPTURE_MODE_MINIMIZE_LATENCY)
                .build()

            try {
                provider.unbindAll()
                provider.bindToLifecycle(this, CameraSelector.DEFAULT_BACK_CAMERA, preview, imageCapture)
            } catch (e: Exception) {
                Toast.makeText(this, "Camera bind failed: ${e.message}", Toast.LENGTH_LONG).show()
            }
        }, ContextCompat.getMainExecutor(this))
    }

    private fun takePhoto() {
        val ic = imageCapture ?: return
        val fileName = SimpleDateFormat("yyyyMMdd-HHmmss", Locale.US)
            .format(System.currentTimeMillis()) + ".jpg"

        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            // ANDROID 10+: Save to public /Gymphotos via MediaStore
            val values = ContentValues().apply {
                put(MediaStore.MediaColumns.DISPLAY_NAME, fileName)
                put(MediaStore.MediaColumns.MIME_TYPE, "image/jpeg")
                // This creates a top-level public folder named Gymphotos
                put(MediaStore.MediaColumns.RELATIVE_PATH, "Gymphotos")
            }
            val collection = MediaStore.Images.Media.getContentUri(MediaStore.VOLUME_EXTERNAL_PRIMARY)
            val options = ImageCapture.OutputFileOptions.Builder(contentResolver, collection, values).build()

            ic.takePicture(
                options,
                ContextCompat.getMainExecutor(this),
                object : ImageCapture.OnImageSavedCallback {
                    override fun onError(exc: ImageCaptureException) {
                        Toast.makeText(this@MainActivity, "Save failed: ${exc.message}", Toast.LENGTH_LONG).show()
                    }
                    override fun onImageSaved(output: ImageCapture.OutputFileResults) {
                        val uri = output.savedUri
                        if (uri == null) {
                            Toast.makeText(this@MainActivity, "Saved, but URI null (MediaStore).", Toast.LENGTH_SHORT).show()
                        } else {
                            Toast.makeText(this@MainActivity, "Saved to /Gymphotos\n$uri", Toast.LENGTH_SHORT).show()
                        }
                    }
                }
            )
        } else {
            // ANDROID 9-: Save by File into /storage/emulated/0/Gymphotos (needs WRITE permission)
            val root = Environment.getExternalStorageDirectory()
            val dir = File(root, "Gymphotos").apply { if (!exists()) mkdirs() }
            val photoFile = File(dir, fileName)
            val options = ImageCapture.OutputFileOptions.Builder(photoFile).build()

            ic.takePicture(
                options,
                ContextCompat.getMainExecutor(this),
                object : ImageCapture.OnImageSavedCallback {
                    override fun onError(exc: ImageCaptureException) {
                        Toast.makeText(this@MainActivity, "Save failed: ${exc.message}", Toast.LENGTH_LONG).show()
                    }
                    override fun onImageSaved(output: ImageCapture.OutputFileResults) {
                        Toast.makeText(this@MainActivity, "Saved to /Gymphotos\n${photoFile.toUri()}", Toast.LENGTH_SHORT).show()
                    }
                }
            )
        }
    }
}
