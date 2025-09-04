import MCL_microdrive as md

if __name__ == '__main__':
    driver = md.MicroDrive()

    print(driver.getPosition())

    value = float(input())
    new_position = driver.moveRelativeAxis(1, value, velocity=1)
    print(new_position)