#
# Adapted from HOME OF SPECTRUM 48  https://softspectrum48.weebly.com/
#
# Handles Beta Disk drive operation.
#

import os
from tkinter import messagebox, filedialog
import app_globals

class BetaDiskDrive:
    #
    # Creates a disk drive object with no disk loaded.
    #
    def __init__(self, id, name):
        self.id = id
        self.name = name
        self.filename = None
        self.disk_type = 0
        # disk geometry        
        self.number_of_sides = 0
        self.number_of_tracks_per_side = 0
        self.number_of_tracks = 0
        self.number_of_sectors = 16
        self.bytes_per_sector = 256
        self.density = 0
        self.size = 0

        # Disk buffer
        self.track_sector_byte = None
        self.dirty = 0

        # Status information.
        self.disk_loaded = 0
        self.current_track = 0
        self.current_sector = 0
        self.current_side = 0
        self.current_step_direction = 0
        self.index_status = 0

    def track0_status(self):
        return 1 if self.current_track == 0 else 0

    #
    # Navigates to a track.
    #
    def seek(self, track):
        if self.disk_loaded:
            self.current_track = track
            self.index_status = 1
        else:
            self.index_status = 0

    #
    # Navigates to track 0.
    #
    def restore(self):
        self.seek(0)

    #
    # Steps to the next higher track number.
    #
    def step_in(self):
        self.current_step_direction = 1
        self.step()

    #
    # Steps to the next lower track number.
    #
    def step_out(self):
        self.current_step_direction = -1
        self.step()

    #
    # Steps to the next track in the same direction as the last step.
    #
    def step(self):
        if self.disk_loaded:
            self.current_track += self.current_step_direction
            if self.current_track < 0: self.current_track = 0
            if self.current_track > self.number_of_tracks: self.current_track = self.number_of_tracks

    #
    # Reads a sector.
    #
    def read_sector(self, position):
        if self.disk_loaded:
            data = 0

            virtual_track = self.current_track * 2 + self.current_side
            try:
                 # Sectors are numbered 1..n, whereas the sector array is numbered 0..n-1.
                data = self.track_sector_byte[virtual_track][self.current_sector - 1][position]
            except:
                data = 0
                #self.log(f"read_sector {self.current_side} {self.current_track=} {self.current_sector=} {position}")

            self.index_status = 0

            return data
        else:
            return 0

    #
    # Reads a sector.
    #
    def write_sector(self, position, data):
        if self.disk_loaded:
            err = 0

            virtual_track = self.current_track * 2 + self.current_side
            try:
                 # Sectors are numbered 1..n, whereas the sector array is numbered 0..n-1.
                self.track_sector_byte[virtual_track][self.current_sector - 1][position] = data
                self.dirty = 1
            except:
                err = 1
                #self.log(f"write_sector {self.current_side} {self.current_track=} {self.current_sector=} {position}")

            self.index_status = 0

            return err
        else:
            return 0

    #
    # Converts a SCL image array to TRD format.
    #
    def scl_to_trd(self, fileName, scl_image):
        trd_image = [0 for _ in range(655360)]

        num_of_files = scl_image[8]

        filepath, file = os.path.split(fileName)
        file, ext = os.path.splitext(file)
        disk_name = file.encode('ascii')

        # Populate FAT.
        start_sector = 0
        total_file_length = 0
        start_track = 1 # Since Track 0 is reserved for FAT and Disk Specification.

        for i in range(0, num_of_files):
            fileLength = scl_image[9 + 14 * i + 13]
            total_file_length += fileLength
            for j in range(0, 14):
                trd_image[16 * i + j] = scl_image[9 + 14 * i + j]

            trd_image[16 * i + 14] = start_sector
            trd_image[16 * i + 15] = start_track

            new_start_track = int((start_track * 16 + start_sector + fileLength) / 16)
            start_sector = (start_track * 16 + start_sector + fileLength) - 16 * new_start_track
            start_track = new_start_track

        # Populate Disk Specification.
        trd_image[2048 + 225] = start_sector
        trd_image[2048 + 226] = start_track
        trd_image[2048 + 227] = 22 # Disk Type
        trd_image[2048 + 228] = num_of_files # File Count
        free_sectors = 2560 - (start_track * 16 + start_sector)
        trd_image[2048 + 230] = int(free_sectors / 256)
        trd_image[2048 + 229] = free_sectors - 256 * trd_image[2048 + 230]
        trd_image[2048 + 231] = 16

        for i in range(0, 9):
            trd_image[2048 + 234 + i] = 32

        # Store the image file name in the disk label section of the Disk Specification.
        i = 0
        while i < len(disk_name) and i < 8:
            trd_image[2048 + 245 + i] = disk_name[i]
            i += 1

        # Poplulate Data Sectors.
        i = 0
        while i < total_file_length * 256:
            trd_image[4096 + i] = scl_image[9 + num_of_files * 14 + i]
            i += 1

        return trd_image

    #
    #   media user handling
    #

    #
    # Loads a disk image file.
    #
    def load_disk(self, disk_image):
        # Eject any disk already in the drive
        # Abort the insert if we want to keep the current disk

        if self.disk_loaded:
            if not self.eject_disk():
                return 0

        # Load the raw image file into a byte array.
        fh = open(disk_image, "rb")
        dim = fh.read()
        fh.close()

        filepath, ext = os.path.splitext(disk_image)
        ext  = ext.lower()

        if ext == ".scl":
            dim = self.scl_to_trd(disk_image, dim)

        fileAllocationTable = dim[0:2048]
        diskSpecification = dim[2048:2048+256]

        # Determine disk type.
        self.disk_type = diskSpecification[227]
        match self.disk_type:
            case 22:
                self.number_of_tracks_per_side = 80
                self.number_of_sides = 2
            case 23:
                self.number_of_tracks_per_side = 40
                self.number_of_sides = 2
            case 24:
                self.number_of_tracks_per_side = 80
                self.number_of_sides = 1
            case 25:
                self.number_of_tracks_per_side = 40
                self.number_of_sides = 1

        self.number_of_tracks = self.number_of_tracks_per_side * self.number_of_sides
        self.size = self.number_of_sectors * self.bytes_per_sector * self.number_of_tracks
        if self.size != len(dim):
            messagebox.showwarning(app_globals.APP_NAME, f"unmanaged disk size")    
            return 0

        # Create a jagged array [Track][Sector][Byte] to hold the TRD image data in a structure of track and sectors.
        # which is easy to access by the FDC.
        self.track_sector_byte = [0] * self.number_of_tracks      #[[0] * self.number_of_sectors][[0] * self.bytes_per_sector]
        track = 0
        while track < self.number_of_tracks:
            self.track_sector_byte[track] = [0] * self.number_of_sectors

            for sector in range(0, self.number_of_sectors):
                self.track_sector_byte[track][sector] = bytearray(self.bytes_per_sector)
            track += 1

        # load track_sector_byte array form disk_image
        i = 0
        for t in range(0, self.number_of_tracks):
            for s in range(0, self.number_of_sectors):
                for b in range(0, self.bytes_per_sector):
                    self.track_sector_byte[t][s][b] = dim[i]
                    i += 1

        self.filename = disk_image
        self.dirty = 0
        self.disk_loaded = True
        self.current_track = 0
        self.current_sector = 0
        return 1

    def save_disk(self, filename=None):
        #emulation_pause()

        if filename is None:
            if not self.filename is None:
                filename = self.filename
            else:
                title = f"{app_globals.APP_NAME} - Save {self.name}"
                filename = filedialog.askopenfilename(title=title, filetypes=[('Disk TRD', '*.trd'), ('All files', '*.*')])
                if not filename:
                    #emulation_unpause()
                    return 0

        # Save disk buffer
        with open(filename, 'wb') as file:
            for t in range(0, self.number_of_tracks):
                for s in range(0, self.number_of_sectors):
                    file.write(self.track_sector_byte[t][s])

        #emulation_unpause()
        self.dirty = 0
        return 1

    def eject_disk(self):
        if not self.disk_loaded:
            return 1

        if self.dirty:
            confirm = messagebox.askyesnocancel(app_globals.APP_NAME, f"{self.name} has been modified.\n" + "Do you want to save it?")
            if confirm is True:         # yes
                return self.save_disk()
            elif confirm is False:      # no
                return 1
            elif confirm is None:       # cancel
                return 0

        self.disk_loaded = 0
        self.dirty = 0
        return 1

    def log(self, text):
        log = open('./tmp/betadisk.log', 'a')
        log.write(f"drive {text}\n")
        log.close
